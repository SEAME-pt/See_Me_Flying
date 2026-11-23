#include "msp/transport.hpp"

#include <cerrno>
#include <cstring>

#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <sys/socket.h>
#include <termios.h>
#include <unistd.h>

namespace msp {

namespace {

std::string errno_text(const std::string& what) {
    return what + ": " + std::strerror(errno);
}

speed_t baud_constant(int baud) {
    switch (baud) {
        case 9600: return B9600;
        case 19200: return B19200;
        case 38400: return B38400;
        case 57600: return B57600;
        case 115200: return B115200;
        case 230400: return B230400;
        case 460800: return B460800;
        case 921600: return B921600;
        default: throw TransportError("unsupported baud rate " + std::to_string(baud));
    }
}

}  // namespace

// ---------- shared fd logic ----------

FdTransport::~FdTransport() {
    if (fd_ >= 0) ::close(fd_);
}

void FdTransport::write_all(const uint8_t* data, size_t len) {
    while (len > 0) {
        ssize_t n = ::write(fd_, data, len);
        if (n < 0) {
            if (errno == EINTR) continue;
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                pollfd p{fd_, POLLOUT, 0};
                ::poll(&p, 1, 100);
                continue;
            }
            throw TransportError(errno_text("write to " + desc_));
        }
        data += n;
        len -= static_cast<size_t>(n);
    }
}

size_t FdTransport::read_some(uint8_t* buf, size_t cap, int timeout_ms) {
    pollfd p{fd_, POLLIN, 0};
    int r = ::poll(&p, 1, timeout_ms < 0 ? 0 : timeout_ms);
    if (r < 0) {
        if (errno == EINTR) return 0;  // a signal (resize, Ctrl-C): let the caller look
        throw TransportError(errno_text("poll " + desc_));
    }
    if (r == 0) return 0;
    ssize_t n = ::read(fd_, buf, cap);
    if (n > 0) return static_cast<size_t>(n);
    if (n == 0) throw TransportError(desc_ + " closed the connection");
    if (errno == EINTR || errno == EAGAIN || errno == EWOULDBLOCK) return 0;
    throw TransportError(errno_text("read from " + desc_));
}

// ---------- TCP (esp-link) ----------

TcpTransport::TcpTransport(const std::string& host, uint16_t port, int connect_timeout_ms) {
    desc_ = host + ":" + std::to_string(port);

    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    addrinfo* res = nullptr;
    int gai = ::getaddrinfo(host.c_str(), std::to_string(port).c_str(), &hints, &res);
    if (gai != 0) throw TransportError("cannot resolve " + host + ": " + ::gai_strerror(gai));

    std::string last_error = "no address found";
    for (addrinfo* ai = res; ai != nullptr && fd_ < 0; ai = ai->ai_next) {
        int fd = ::socket(ai->ai_family, ai->ai_socktype | SOCK_CLOEXEC | SOCK_NONBLOCK,
                          ai->ai_protocol);
        if (fd < 0) {
            last_error = std::strerror(errno);
            continue;
        }
        // Non-blocking connect so an unreachable ESP fails after the timeout
        // instead of the kernel's ~2 minutes.
        int rc = ::connect(fd, ai->ai_addr, ai->ai_addrlen);
        int err = rc == 0 ? 0 : errno;
        if (rc < 0 && errno == EINPROGRESS) {
            pollfd p{fd, POLLOUT, 0};
            rc = ::poll(&p, 1, connect_timeout_ms);
            if (rc == 0) {
                err = ETIMEDOUT;
            } else if (rc < 0) {
                err = errno;
            } else {
                socklen_t len = sizeof err;
                ::getsockopt(fd, SOL_SOCKET, SO_ERROR, &err, &len);
            }
        }
        if (err != 0) {
            last_error = std::strerror(err);
            ::close(fd);
            continue;
        }
        ::fcntl(fd, F_SETFL, ::fcntl(fd, F_GETFL) & ~O_NONBLOCK);
        int one = 1;  // MSP is small request/reply packets: don't let Nagle batch them
        ::setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof one);
        fd_ = fd;
    }
    ::freeaddrinfo(res);
    if (fd_ < 0) throw TransportError("cannot connect to " + desc_ + ": " + last_error);
}

// ---------- serial ----------

SerialTransport::SerialTransport(const std::string& device, int baud) {
    desc_ = device + " @ " + std::to_string(baud);
    speed_t speed = baud_constant(baud);

    fd_ = ::open(device.c_str(), O_RDWR | O_NOCTTY | O_CLOEXEC);
    if (fd_ < 0) throw TransportError(errno_text("cannot open " + device));

    termios tio{};
    if (::tcgetattr(fd_, &tio) != 0) throw TransportError(errno_text("tcgetattr " + device));
    ::cfmakeraw(&tio);
    tio.c_cflag |= CLOCAL | CREAD;
    tio.c_cc[VMIN] = 0;
    tio.c_cc[VTIME] = 0;
    ::cfsetispeed(&tio, speed);
    ::cfsetospeed(&tio, speed);
    if (::tcsetattr(fd_, TCSANOW, &tio) != 0) throw TransportError(errno_text("tcsetattr " + device));
    ::tcflush(fd_, TCIOFLUSH);
}

}  // namespace msp
