// msp_gateway - the single owner of the MSP link to the flight controller.
//
// It connects to esp-link (or a serial port) once, and lets any number of
// clients (msp_dashboard, a ROS node, INAV Configurator, scripts...) connect to
// it instead. Requests from all clients are queued and sent to the FC, each
// reply goes back to the client that asked, and every frame in both directions
// is logged with the client it belongs to.
//
// Up to --max-inflight requests (default 4) are on the wire at once. INAV
// answers queued requests in order, one per 10 ms serial task run, so a few in
// flight hide the Wi-Fi round trip: on the bench (Nov 25-26) 1 in flight gave
// about 45 replies/s and 4-8 gave 85-97. Two limits keep INAV safe:
//   - its UART receive buffer is 256 bytes with no overflow guard, so the
//     requests in flight together stay under --max-inflight-bytes (default 200);
//   - more than 8 in flight only adds delay (16 in flight doubled the round
//     trip with no extra replies), so --max-inflight is capped at 8.
// MSP replies carry no request id: a reply goes to the oldest request in flight
// with the same command and MSP version.
//
//   msp_gateway                                  esp-link at 192.168.4.1:23, clients on :5760
//   msp_gateway --serial /dev/ttyUSB0
//   msp_gateway --verbose                        print every request, not only writes

#include <arpa/inet.h>
#include <fcntl.h>
#include <getopt.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <deque>
#include <fstream>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "msp/frame.hpp"
#include "msp/messages.hpp"
#include "msp/transport.hpp"

namespace {

using Clock = std::chrono::steady_clock;
using msp::Payload;
using msp::RawFrame;

volatile std::sig_atomic_t g_stop = 0;
void on_stop(int) { g_stop = 1; }

constexpr int kGatewayId = 0;          // "client" id for frames the gateway sends itself
constexpr size_t kMaxQueuedPerClient = 32;

// ---------- options ----------

struct Options {
    std::string host = "192.168.4.1";
    int port = 23;
    std::string serial;
    int baud = 115200;
    std::string bind = "0.0.0.0";
    int listen_port = 5760;
    double timeout_s = 0.3;
    int max_inflight = 4;
    int max_inflight_bytes = 200;
    std::string log_path;              // empty = auto-named, "-" = no file
    bool verbose = false;
    bool motor_guard = true;
    int max_clients = 8;
};

void usage(const char* prog) {
    std::printf(
        "The single owner of the MSP link: clients connect here instead of to the ESP.\n"
        "Every request and reply is queued, routed and logged.\n\n"
        "usage: %s [options]\n\n"
        "upstream (the drone):\n"
        "  -H, --host ADDR        esp-link address (default 192.168.4.1)\n"
        "  -p, --port N           esp-link TCP port (default 23)\n"
        "  -s, --serial DEV       use a serial device instead, e.g. /dev/ttyUSB0\n"
        "  -b, --baud N           serial baud rate (default 115200)\n"
        "  -t, --timeout SEC      wait for each FC reply (default 0.3)\n"
        "      --max-inflight N   requests on the wire at once, 1-8 (default 4; 1 = one at a time)\n"
        "      --max-inflight-bytes N\n"
        "                         their total size, to fit INAV's 256-byte UART buffer (default 200)\n\n"
        "clients:\n"
        "      --bind ADDR        address to listen on (default 0.0.0.0 = every interface)\n"
        "  -l, --listen-port N    port clients connect to (default 5760)\n"
        "      --max-clients N    (default 8)\n\n"
        "logging and safety:\n"
        "      --log FILE         JSON-lines log of every frame (default msp_YYYYmmdd_HHMMSS.jsonl,\n"
        "                         '-' for no file)\n"
        "  -v, --verbose          print every request on screen, not only writes and events\n"
        "      --no-motor-guard   don't stop the motors when the client that started them\n"
        "                         disconnects\n",
        prog);
}

std::optional<Options> parse_args(int argc, char** argv) {
    Options o;
    const option longopts[] = {
        {"host", required_argument, nullptr, 'H'},     {"port", required_argument, nullptr, 'p'},
        {"serial", required_argument, nullptr, 's'},   {"baud", required_argument, nullptr, 'b'},
        {"timeout", required_argument, nullptr, 't'},  {"bind", required_argument, nullptr, 1},
        {"listen-port", required_argument, nullptr, 'l'}, {"max-clients", required_argument, nullptr, 2},
        {"log", required_argument, nullptr, 3},        {"verbose", no_argument, nullptr, 'v'},
        {"no-motor-guard", no_argument, nullptr, 4},   {"help", no_argument, nullptr, 'h'},
        {"max-inflight", required_argument, nullptr, 5},
        {"max-inflight-bytes", required_argument, nullptr, 6},
        {nullptr, 0, nullptr, 0},
    };
    int c;
    while ((c = getopt_long(argc, argv, "H:p:s:b:t:l:vh", longopts, nullptr)) != -1) {
        switch (c) {
            case 'H': o.host = optarg; break;
            case 'p': o.port = std::atoi(optarg); break;
            case 's': o.serial = optarg; break;
            case 'b': o.baud = std::atoi(optarg); break;
            case 't': o.timeout_s = std::atof(optarg); break;
            case 1: o.bind = optarg; break;
            case 'l': o.listen_port = std::atoi(optarg); break;
            case 2: o.max_clients = std::atoi(optarg); break;
            case 3: o.log_path = optarg; break;
            case 'v': o.verbose = true; break;
            case 4: o.motor_guard = false; break;
            case 5: o.max_inflight = std::atoi(optarg); break;
            case 6: o.max_inflight_bytes = std::atoi(optarg); break;
            case 'h': usage(argv[0]); std::exit(0);
            default: usage(argv[0]); return std::nullopt;
        }
    }
    if (o.port <= 0 || o.port > 65535 || o.listen_port <= 0 || o.listen_port > 65535 ||
        o.timeout_s <= 0 || o.max_clients < 1) {
        std::fprintf(stderr, "invalid --port, --listen-port, --timeout or --max-clients\n");
        return std::nullopt;
    }
    if (o.max_inflight < 1 || o.max_inflight > 8 || o.max_inflight_bytes < 16 ||
        o.max_inflight_bytes > 256) {
        std::fprintf(stderr, "--max-inflight must be 1-8 and --max-inflight-bytes 16-256\n");
        return std::nullopt;
    }
    return o;
}

// ---------- logging ----------

std::string json_escape(const std::string& s) {
    std::string out;
    for (char ch : s) {
        if (ch == '"' || ch == '\\') out += '\\';
        if (static_cast<unsigned char>(ch) < 0x20) continue;
        out += ch;
    }
    return out;
}

std::string hex(const Payload& p) {
    static const char* d = "0123456789abcdef";
    std::string s;
    for (uint8_t b : p) {
        s += d[b >> 4];
        s += d[b & 15];
    }
    return s;
}

std::string wall_clock(bool with_date) {
    const auto now = std::chrono::system_clock::now();
    const std::time_t tt = std::chrono::system_clock::to_time_t(now);
    const long ms = static_cast<long>(
        std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count() % 1000);
    char buf[40];
    std::strftime(buf, sizeof buf, with_date ? "%Y-%m-%dT%H:%M:%S" : "%H:%M:%S", std::localtime(&tt));
    char out[48];
    std::snprintf(out, sizeof out, "%s.%03ld", buf, ms);
    return out;
}

class Log {
public:
    Log(const std::string& path, bool verbose) : verbose_(verbose), color_(isatty(STDOUT_FILENO)) {
        if (path != "-") {
            path_ = path;
            if (path_.empty()) {
                char name[64];
                const std::time_t tt = std::time(nullptr);
                std::strftime(name, sizeof name, "msp_%Y%m%d_%H%M%S.jsonl", std::localtime(&tt));
                path_ = name;
            }
            file_.open(path_, std::ios::app);
        }
    }
    bool ok() const { return path_.empty() || file_.is_open(); }
    const std::string& path() const { return path_; }

    // One JSON object per line. `fields` is the inside of the object, already JSON.
    void record(const std::string& fields) {
        if (file_.is_open()) file_ << "{\"time\":\"" << wall_clock(true) << "\"," << fields << "}" << std::endl;
    }

    // Screen output: events always; transactions if verbose or if they write.
    void screen(const std::string& line, const char* color = nullptr, bool always = true) {
        if (!always && !verbose_) return;
        if (color_ && color)
            std::printf("%s %s%s\033[0m\n", wall_clock(false).c_str(), color, line.c_str());
        else
            std::printf("%s %s\n", wall_clock(false).c_str(), line.c_str());
        std::fflush(stdout);
    }

private:
    std::string path_;
    std::ofstream file_;
    bool verbose_, color_;
};

constexpr const char* kGreen = "\033[92m";
constexpr const char* kYellow = "\033[93m";
constexpr const char* kRed = "\033[91m";
constexpr const char* kCyan = "\033[96m";

// ---------- gateway ----------

struct Client {
    int id;
    int fd;
    std::string peer;
    msp::StreamParser parser{"<"};   // clients only send requests
    std::vector<uint8_t> out;        // replies not yet written (slow client)
    size_t queued = 0;
    unsigned long requests = 0;
};

struct Request {
    int client_id;
    RawFrame frame;
    Clock::time_point received;
};

struct InFlight {
    Request req;
    Clock::time_point sent;
};

class Gateway {
public:
    Gateway(const Options& o, Log& log) : o_(o), log_(log) {}

    bool listen() {
        listen_fd_ = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
        int one = 1;
        ::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(static_cast<uint16_t>(o_.listen_port));
        if (::inet_pton(AF_INET, o_.bind.c_str(), &addr.sin_addr) != 1) {
            std::fprintf(stderr, "--bind must be an IPv4 address\n");
            return false;
        }
        if (::bind(listen_fd_, reinterpret_cast<sockaddr*>(&addr), sizeof addr) != 0 ||
            ::listen(listen_fd_, 8) != 0) {
            std::fprintf(stderr, "cannot listen on %s:%d: %s\n", o_.bind.c_str(), o_.listen_port,
                         std::strerror(errno));
            return false;
        }
        return true;
    }

    void run() {
        connect_upstream();
        while (!g_stop) {
            dispatch();
            std::vector<pollfd> fds;
            fds.push_back({listen_fd_, POLLIN, 0});
            const bool had_up = static_cast<bool>(up_);   // up_ can change before we read revents
            if (had_up) fds.push_back({up_->fd(), POLLIN, 0});
            std::vector<int> ids;
            for (auto& [id, c] : clients_) {
                fds.push_back({c.fd, static_cast<short>(POLLIN | (c.out.empty() ? 0 : POLLOUT)), 0});
                ids.push_back(id);
            }

            const int r = ::poll(fds.data(), fds.size(), wait_ms());
            if (r < 0 && errno != EINTR) break;

            check_timeout();
            if (!up_ && Clock::now() >= next_reconnect_) connect_upstream();
            if (r <= 0) continue;

            size_t k = 0;
            if (fds[k++].revents & POLLIN) accept_clients();
            if (had_up && (fds[k++].revents & (POLLIN | POLLHUP | POLLERR)) && up_) read_upstream();
            for (size_t i = 0; i < ids.size(); ++i, ++k) {
                auto it = clients_.find(ids[i]);
                if (it == clients_.end()) continue;
                if (fds[k].revents & POLLOUT) flush(it->second);
                if (fds[k].revents & (POLLIN | POLLHUP | POLLERR)) read_client(ids[i]);
            }
        }
        shutdown();
    }

private:
    // ----- upstream (the FC) -----

    void connect_upstream() {
        try {
            if (o_.serial.empty())
                up_ = std::make_unique<msp::TcpTransport>(o_.host, static_cast<uint16_t>(o_.port), 2000);
            else
                up_ = std::make_unique<msp::SerialTransport>(o_.serial, o_.baud);
            up_parser_ = msp::StreamParser(">!");
            log_.screen("upstream connected: " + up_->describe(), kGreen);
            log_.record("\"event\":\"upstream_up\",\"link\":\"" + json_escape(up_->describe()) + "\"");
        } catch (const msp::TransportError& e) {
            up_.reset();
            if (!upstream_error_logged_) {
                log_.screen(std::string("upstream unavailable (retrying every 2 s): ") + e.what(), kRed);
                log_.record("\"event\":\"upstream_down\",\"error\":\"" + json_escape(e.what()) + "\"");
                upstream_error_logged_ = true;
            }
            next_reconnect_ = Clock::now() + std::chrono::seconds(2);
            return;
        }
        upstream_error_logged_ = false;
    }

    void upstream_lost(const std::string& why) {
        log_.screen("upstream lost: " + why, kRed);
        log_.record("\"event\":\"upstream_down\",\"error\":\"" + json_escape(why) + "\"");
        if (motor_owner_)
            log_.screen("WARNING: motors were spinning when the link dropped - they could not be stopped", kRed);
        up_.reset();
        upstream_error_logged_ = true;
        next_reconnect_ = Clock::now() + std::chrono::seconds(2);
        for (const InFlight& in : inflight_) log_transaction(in.req, nullptr, "link_lost", in.sent);
        inflight_.clear();
        inflight_bytes_ = 0;
    }

    void read_upstream() {
        uint8_t buf[1024];
        size_t n = 0;
        try {
            n = up_->read_some(buf, sizeof buf, 0);
        } catch (const msp::TransportError& e) {
            upstream_lost(e.what());
            return;
        }
        up_parser_.feed(buf, n);
        while (auto f = up_parser_.next()) {
            // INAV answers in order, so the oldest request with this command is the one answered.
            const auto it = std::find_if(inflight_.begin(), inflight_.end(), [&](const InFlight& in) {
                return in.req.frame.cmd == f->cmd && in.req.frame.version == f->version;
            });
            if (it != inflight_.end()) {
                const InFlight in = std::move(*it);
                inflight_bytes_ -= in.req.frame.bytes.size();
                inflight_.erase(it);
                deliver(in, *f);
            } else {
                // Nobody asked for this right now (e.g. a late reply after a timeout).
                log_.record("\"event\":\"unsolicited\",\"v\":" + std::to_string(f->version) +
                            ",\"cmd\":" + std::to_string(f->cmd) + ",\"name\":\"" +
                            msp::command_name(f->cmd) + "\",\"ok\":" + (f->direction == '>' ? "true" : "false") +
                            ",\"len\":" + std::to_string(f->payload.size()) + ",\"payload\":\"" +
                            hex(f->payload) + "\"");
            }
        }
    }

    // Sends queued requests while there is room on the wire: fewer than
    // --max-inflight waiting for a reply, and their bytes under --max-inflight-bytes.
    void dispatch() {
        while (!queue_.empty() && inflight_.size() < static_cast<size_t>(o_.max_inflight)) {
            const size_t size = queue_.front().frame.bytes.size();
            // An oversized request still goes, but only on an empty line.
            if (!inflight_.empty() && inflight_bytes_ + size > static_cast<size_t>(o_.max_inflight_bytes))
                break;
            Request req = std::move(queue_.front());
            queue_.pop_front();
            if (auto it = clients_.find(req.client_id); it != clients_.end() && it->second.queued > 0)
                --it->second.queued;
            if (!up_) {
                log_transaction(req, nullptr, "upstream_down");
                continue;
            }
            try {
                up_->write_all(req.frame.bytes.data(), req.frame.bytes.size());
            } catch (const msp::TransportError& e) {
                log_transaction(req, nullptr, "link_lost");
                upstream_lost(e.what());
                continue;
            }
            inflight_bytes_ += size;
            inflight_.push_back(InFlight{std::move(req), Clock::now()});
        }
    }

    // inflight_ is in send order, so the oldest request, the first to time out, is at the front.
    void check_timeout() {
        while (!inflight_.empty() && Clock::now() - inflight_.front().sent > timeout()) {
            const InFlight in = std::move(inflight_.front());
            inflight_.pop_front();
            inflight_bytes_ -= in.req.frame.bytes.size();
            log_transaction(in.req, nullptr, "timeout", in.sent);
        }
    }

    // ----- clients -----

    void accept_clients() {
        for (;;) {
            sockaddr_in addr{};
            socklen_t len = sizeof addr;
            const int fd = ::accept4(listen_fd_, reinterpret_cast<sockaddr*>(&addr), &len,
                                     SOCK_CLOEXEC | SOCK_NONBLOCK);
            if (fd < 0) return;
            char ip[INET_ADDRSTRLEN] = "?";
            ::inet_ntop(AF_INET, &addr.sin_addr, ip, sizeof ip);
            const std::string peer = std::string(ip) + ":" + std::to_string(ntohs(addr.sin_port));
            if (static_cast<int>(clients_.size()) >= o_.max_clients) {
                log_.screen("refused " + peer + ": already " + std::to_string(o_.max_clients) + " clients", kYellow);
                ::close(fd);
                continue;
            }
            int one = 1;
            ::setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof one);
            const int id = next_id_++;
            clients_.emplace(id, Client{id, fd, peer, msp::StreamParser("<"), {}, 0, 0});
            log_.screen("client #" + std::to_string(id) + " connected from " + peer, kCyan);
            log_.record("\"event\":\"connect\",\"client\":" + std::to_string(id) + ",\"peer\":\"" + peer + "\"");
        }
    }

    void read_client(int id) {
        Client& c = clients_.at(id);
        uint8_t buf[1024];
        const ssize_t n = ::recv(c.fd, buf, sizeof buf, 0);
        if (n == 0 || (n < 0 && errno != EAGAIN && errno != EINTR)) {
            drop_client(id, n == 0 ? "disconnected" : std::strerror(errno));
            return;
        }
        if (n < 0) return;
        c.parser.feed(buf, static_cast<size_t>(n));
        while (auto f = c.parser.next()) {
            ++c.requests;
            if (c.queued >= kMaxQueuedPerClient) {
                log_.screen("#" + std::to_string(id) + " " + msp::command_name(f->cmd) +
                                " dropped: client is sending faster than the FC can answer", kRed);
                log_.record("\"event\":\"dropped\",\"client\":" + std::to_string(id) +
                            ",\"reason\":\"queue full\",\"cmd\":" + std::to_string(f->cmd));
                continue;
            }
            ++c.queued;
            queue_.push_back(Request{id, std::move(*f), Clock::now()});
        }
    }

    void flush(Client& c) {
        while (!c.out.empty()) {
            const ssize_t n = ::send(c.fd, c.out.data(), c.out.size(), MSG_NOSIGNAL);
            if (n <= 0) return;   // EAGAIN: wait for POLLOUT; errors show up on the next read
            c.out.erase(c.out.begin(), c.out.begin() + n);
        }
    }

    void drop_client(int id, const std::string& why) {
        auto it = clients_.find(id);
        if (it == clients_.end()) return;
        log_.screen("client #" + std::to_string(id) + " (" + it->second.peer + ") " + why + " after " +
                        std::to_string(it->second.requests) + " requests",
                    kCyan);
        log_.record("\"event\":\"disconnect\",\"client\":" + std::to_string(id) + ",\"reason\":\"" +
                    json_escape(why) + "\"");
        ::close(it->second.fd);
        clients_.erase(it);
        // Its queued requests have nobody to answer to.
        for (auto q = queue_.begin(); q != queue_.end();)
            q = q->client_id == id ? queue_.erase(q) : q + 1;

        if (o_.motor_guard && motor_owner_ == id) {
            log_.screen("client #" + std::to_string(id) + " left the motors spinning - stopping them", kRed);
            std::array<uint16_t, 8> stop;
            stop.fill(1000);
            queue_.push_front(Request{kGatewayId, msp::make_request_v2(msp::cmd::SET_MOTOR,
                                                                       msp::encode_set_motor(stop)),
                                      Clock::now()});
        }
    }

    // ----- replies -----

    void deliver(const InFlight& in, const RawFrame& reply) {
        log_transaction(in.req, &reply, reply.direction == '>' ? "ok" : "error", in.sent);
        track_motors(in.req, reply);
        if (in.req.client_id == kGatewayId) return;
        auto it = clients_.find(in.req.client_id);
        if (it == clients_.end()) return;   // the client left while we waited
        Client& c = it->second;
        c.out.insert(c.out.end(), reply.bytes.begin(), reply.bytes.end());
        flush(c);
    }

    // Remembers which client last set the motors spinning, for the motor guard.
    void track_motors(const Request& req, const RawFrame& reply) {
        if (req.frame.cmd != msp::cmd::SET_MOTOR || reply.direction != '>') return;
        bool spinning = false;
        for (size_t i = 0; i + 1 < req.frame.payload.size() && i < 16; i += 2)
            if ((req.frame.payload[i] | req.frame.payload[i + 1] << 8) > 1000) spinning = true;
        motor_owner_ = spinning ? std::optional<int>(req.client_id) : std::nullopt;
    }

    // `sent` is when the request went on the wire; nullopt if it never did.
    void log_transaction(const Request& req, const RawFrame* reply, const char* result,
                         std::optional<Clock::time_point> sent = std::nullopt) {
        const auto now = Clock::now();
        const long wait_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                                 sent.value_or(now) - req.received).count();
        const long latency_ms =
            sent ? std::chrono::duration_cast<std::chrono::milliseconds>(now - *sent).count() : 0;
        const std::string name = msp::command_name(req.frame.cmd);
        const bool write = msp::is_write_command(req.frame.cmd);

        std::string rec = "\"event\":\"transaction\",\"client\":" + std::to_string(req.client_id) +
                          ",\"peer\":\"" + peer_of(req.client_id) + "\",\"v\":" +
                          std::to_string(req.frame.version) + ",\"cmd\":" + std::to_string(req.frame.cmd) +
                          ",\"name\":\"" + name + "\",\"write\":" + (write ? "true" : "false") +
                          ",\"request\":\"" + hex(req.frame.payload) + "\",\"result\":\"" + result + "\"";
        if (reply) rec += ",\"reply\":\"" + hex(reply->payload) + "\"";
        rec += ",\"queue_ms\":" + std::to_string(wait_ms) + ",\"latency_ms\":" + std::to_string(latency_ms);
        log_.record(rec);

        std::string line = "#" + std::to_string(req.client_id) + " " + name;
        if (!req.frame.payload.empty()) line += " [" + hex(req.frame.payload) + "]";
        line += std::string("  ") + result + (reply ? " " + std::to_string(latency_ms) + " ms" : "");
        const bool ok = std::strcmp(result, "ok") == 0;
        log_.screen(line, ok ? (write ? kYellow : nullptr) : kRed, write || !ok);
    }

    std::string peer_of(int id) const {
        if (id == kGatewayId) return "gateway";
        auto it = clients_.find(id);
        return it == clients_.end() ? "gone" : it->second.peer;
    }

    std::chrono::milliseconds timeout() const {
        return std::chrono::milliseconds(static_cast<long>(o_.timeout_s * 1000));
    }

    int wait_ms() const {
        long ms = 1000;
        if (!inflight_.empty()) {
            const auto left = std::chrono::duration_cast<std::chrono::milliseconds>(
                inflight_.front().sent + timeout() - Clock::now()).count();
            ms = std::max(0L, std::min(ms, left + 1));
        }
        if (!up_) {
            const auto left = std::chrono::duration_cast<std::chrono::milliseconds>(
                next_reconnect_ - Clock::now()).count();
            ms = std::max(0L, std::min(ms, left));
        }
        return static_cast<int>(ms);
    }

    void shutdown() {
        // Leaving with motors spinning: stop them before letting go of the link.
        if (motor_owner_ && up_) {
            log_.screen("stopping the motors before exit", kRed);
            std::array<uint16_t, 8> stop;
            stop.fill(1000);
            const RawFrame f = msp::make_request_v2(msp::cmd::SET_MOTOR, msp::encode_set_motor(stop));
            try {
                up_->write_all(f.bytes.data(), f.bytes.size());
            } catch (const msp::TransportError&) {
            }
        }
        for (auto& [id, c] : clients_) ::close(c.fd);
        if (listen_fd_ >= 0) ::close(listen_fd_);
        log_.record("\"event\":\"stopped\"");
    }

    const Options& o_;
    Log& log_;
    int listen_fd_ = -1;
    std::unique_ptr<msp::FdTransport> up_;
    msp::StreamParser up_parser_{">!"};
    bool upstream_error_logged_ = false;
    Clock::time_point next_reconnect_{};
    std::map<int, Client> clients_;
    int next_id_ = 1;
    std::deque<Request> queue_;
    std::deque<InFlight> inflight_;   // sent, waiting for a reply; oldest first
    size_t inflight_bytes_ = 0;
    std::optional<int> motor_owner_;
};

}  // namespace

int main(int argc, char** argv) {
    const auto opts = parse_args(argc, argv);
    if (!opts) return 2;

    struct sigaction sa {};
    sa.sa_handler = on_stop;
    sigaction(SIGINT, &sa, nullptr);
    sigaction(SIGTERM, &sa, nullptr);
    sigaction(SIGHUP, &sa, nullptr);
    std::signal(SIGPIPE, SIG_IGN);

    Log log(opts->log_path, opts->verbose);
    if (!log.ok()) {
        std::fprintf(stderr, "cannot open the log file %s\n", log.path().c_str());
        return 1;
    }
    Gateway gw(*opts, log);
    if (!gw.listen()) return 1;

    log.screen("msp_gateway listening on " + opts->bind + ":" + std::to_string(opts->listen_port) +
               (log.path().empty() ? "  (no log file)" : "  ·  logging to " + log.path()));
    log.screen("up to " + std::to_string(opts->max_inflight) + " requests in flight, " +
               std::to_string(opts->max_inflight_bytes) + " bytes at most");
    log.screen(opts->verbose ? "showing every request" : "showing writes, errors and connections (-v for everything)");
    gw.run();
    log.screen("gateway stopped");
    return 0;
}
