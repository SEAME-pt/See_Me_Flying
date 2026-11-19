#include "terminal.hpp"

#include <cerrno>
#include <poll.h>
#include <sys/ioctl.h>
#include <unistd.h>

namespace dash {

Terminal::Terminal() {
    if (::tcgetattr(STDIN_FILENO, &saved_) == 0) {
        termios raw = saved_;
        raw.c_lflag &= ~static_cast<tcflag_t>(ICANON | ECHO);  // keys arrive at once, unechoed
        raw.c_cc[VMIN] = 0;
        raw.c_cc[VTIME] = 0;
        restore_ = ::tcsetattr(STDIN_FILENO, TCSANOW, &raw) == 0;
    }
    write("\033[?1049h\033[?25l");  // alternate screen, hide cursor
}

Terminal::~Terminal() {
    write("\033[0m\033[?25h\033[?1049l");  // reset colors, show cursor, back to normal screen
    if (restore_) ::tcsetattr(STDIN_FILENO, TCSANOW, &saved_);
}

Terminal::Size Terminal::size() {
    winsize ws{};
    if (::ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) == 0 && ws.ws_col > 0 && ws.ws_row > 0)
        return {ws.ws_col, ws.ws_row};
    return {100, 40};
}

int Terminal::read_key(int timeout_ms) {
    pollfd p{STDIN_FILENO, POLLIN, 0};
    if (::poll(&p, 1, timeout_ms < 0 ? 0 : timeout_ms) <= 0) return -1;
    unsigned char c;
    return ::read(STDIN_FILENO, &c, 1) == 1 ? c : -1;
}

void Terminal::write(const std::string& s) {
    const char* data = s.data();
    size_t left = s.size();
    while (left > 0) {
        ssize_t n = ::write(STDOUT_FILENO, data, left);
        if (n < 0) {
            if (errno == EINTR) continue;
            return;
        }
        data += n;
        left -= static_cast<size_t>(n);
    }
}

}  // namespace dash
