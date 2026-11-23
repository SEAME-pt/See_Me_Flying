// msp_dashboard - live INAV telemetry over MSP, shown as a table whose values
// update in place.
//
//   msp_dashboard                              esp-link at 192.168.4.1:23
//   msp_dashboard --host 192.168.4.1 --port 23
//   msp_dashboard --serial /dev/ttyUSB0        through a USB serial bridge
//   msp_dashboard --enable-motors              allow motor-test commands (props off!)
//
// Keys: q quit, r redraw, : type a command, space STOP all motors.

#include <getopt.h>
#include <unistd.h>

#include <chrono>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "command_panel.hpp"
#include "console.hpp"
#include "dashboard.hpp"
#include "fields.hpp"
#include "msp/client.hpp"
#include "msp/commander.hpp"
#include "msp/poller.hpp"
#include "msp/telemetry.hpp"
#include "msp/transport.hpp"
#include "terminal.hpp"

namespace {

volatile std::sig_atomic_t g_stop = 0;
volatile std::sig_atomic_t g_resized = 0;

void on_stop(int) { g_stop = 1; }
void on_resize(int) { g_resized = 1; }

void install_signals() {
    struct sigaction sa {};
    sa.sa_handler = on_stop;   // no SA_RESTART: blocking waits return early
    sigaction(SIGINT, &sa, nullptr);
    sigaction(SIGTERM, &sa, nullptr);
    sigaction(SIGHUP, &sa, nullptr);   // SSH session dropped: still stop the motors on the way out
    sa.sa_handler = on_resize;
    sigaction(SIGWINCH, &sa, nullptr);
    std::signal(SIGPIPE, SIG_IGN);  // a dropped socket becomes an error, not a crash
}

void error(const std::string& msg) {
    if (isatty(STDERR_FILENO))
        std::fprintf(stderr, "\033[91m%s\033[0m\n", msg.c_str());
    else
        std::fprintf(stderr, "%s\n", msg.c_str());
}

struct Options {
    std::string host = "192.168.4.1";   // esp-link's own AP address
    int port = 23;                      // esp-link's serial bridge port
    std::string serial;                 // set to use a serial device instead of TCP
    int baud = 115200;
    double rate_hz = 5.0;
    double timeout_s = 0.4;
    msp::MotorLimits motors;           // motor test is off unless --enable-motors
    std::string cmd_log;               // file to append the command log to
};

void usage(const char* prog) {
    std::printf(
        "Live INAV telemetry over MSP, shown as a table that updates in place.\n\n"
        "usage: %s [options]\n\n"
        "connection (TCP is the default):\n"
        "  -H, --host ADDR      ESP bridge address (default 192.168.4.1)\n"
        "  -p, --port N         ESP bridge TCP port (default 23, esp-link's serial bridge)\n"
        "  -s, --serial DEV     use a serial device instead, e.g. /dev/ttyUSB0\n"
        "  -b, --baud N         serial baud rate (default 115200)\n\n"
        "polling:\n"
        "  -r, --rate HZ        polling cycles per second (default 5)\n"
        "  -t, --timeout SEC    wait per reply before 'no reply' (default 0.4)\n\n"
        "commands:\n"
        "  --enable-motors      allow motor-test commands (MSP_SET_MOTOR). PROPS OFF.\n"
        "  --motor-max N        highest motor value accepted (default 1500)\n"
        "  --motor-timeout SEC  stop the motors after SEC without a new command\n"
        "                       (default 15, 0 = never)\n"
        "  --motor-count N      number of motors (default 4)\n"
        "  --cmd-log FILE       also append every command and its result to FILE\n\n"
        "while running:\n"
        "  :      type a command (help, motor <n> <value>, motors <value>, stop)\n"
        "  space  STOP all motors        q  quit        r  redraw\n",
        prog);
}

std::optional<Options> parse_args(int argc, char** argv) {
    Options o;
    const option longopts[] = {
        {"host", required_argument, nullptr, 'H'},  {"port", required_argument, nullptr, 'p'},
        {"serial", required_argument, nullptr, 's'}, {"baud", required_argument, nullptr, 'b'},
        {"rate", required_argument, nullptr, 'r'},  {"timeout", required_argument, nullptr, 't'},
        {"enable-motors", no_argument, nullptr, 1},  {"motor-max", required_argument, nullptr, 2},
        {"motor-timeout", required_argument, nullptr, 3}, {"motor-count", required_argument, nullptr, 4},
        {"cmd-log", required_argument, nullptr, 5},
        {"help", no_argument, nullptr, 'h'},        {nullptr, 0, nullptr, 0},
    };
    int c;
    while ((c = getopt_long(argc, argv, "H:p:s:b:r:t:h", longopts, nullptr)) != -1) {
        switch (c) {
            case 'H': o.host = optarg; break;
            case 'p': o.port = std::atoi(optarg); break;
            case 's': o.serial = optarg; break;
            case 'b': o.baud = std::atoi(optarg); break;
            case 'r': o.rate_hz = std::atof(optarg); break;
            case 't': o.timeout_s = std::atof(optarg); break;
            case 1: o.motors.enabled = true; break;
            case 2: o.motors.max_value = static_cast<uint16_t>(std::atoi(optarg)); break;
            case 3: o.motors.auto_stop_s = std::atoi(optarg); break;
            case 4: o.motors.motor_count = std::atoi(optarg); break;
            case 5: o.cmd_log = optarg; break;
            case 'h': usage(argv[0]); std::exit(0);
            default: usage(argv[0]); return std::nullopt;
        }
    }
    if (o.port <= 0 || o.port > 65535 || o.rate_hz <= 0 || o.timeout_s <= 0) {
        error("invalid --port, --rate or --timeout value");
        return std::nullopt;
    }
    if (o.motors.max_value < 1000 || o.motors.max_value > 2000 || o.motors.motor_count < 1 ||
        o.motors.motor_count > 8 || o.motors.auto_stop_s < 0) {
        error("--motor-max must be 1000-2000, --motor-count 1-8, --motor-timeout 0 or more");
        return std::nullopt;
    }
    return o;
}

}  // namespace

int main(int argc, char** argv) {
    const auto opts = parse_args(argc, argv);
    if (!opts) return 2;
    if (!isatty(STDOUT_FILENO)) {
        error("msp_dashboard needs a terminal. For logs/pipes use inav_telemetry.py --info.");
        return 2;
    }
    install_signals();

    // ---- connect ----
    std::unique_ptr<msp::Transport> transport;
    try {
        if (opts->serial.empty())
            transport = std::make_unique<msp::TcpTransport>(opts->host, static_cast<uint16_t>(opts->port));
        else
            transport = std::make_unique<msp::SerialTransport>(opts->serial, opts->baud);
    } catch (const msp::TransportError& e) {
        error(std::string("Could not open the bridge: ") + e.what());
        if (opts->serial.empty())
            error("Check that this computer is on the ESP's Wi-Fi network, and that --host/--port\n"
                  "match esp-link (192.168.4.1, port 23 by default).");
        return 1;
    }

    msp::Telemetry telemetry;
    telemetry.link = transport->describe();
    msp::Client client(*transport);
    msp::Poller poller(client, telemetry, static_cast<int>(opts->timeout_s * 1000));

    std::fprintf(stderr, "Connected to %s - reading flight controller info...\n", telemetry.link.c_str());
    try {
        if (!poller.read_static()) {
            error("Connected to the bridge, but the flight controller is not answering.\n"
                  "Check that it is powered, that TX/RX are crossed (FC TX -> ESP RX),\n"
                  "and that MSP is enabled at 115200 on that UART in INAV's Ports tab.");
            return 1;
        }
    } catch (const msp::TransportError& e) {
        error(std::string("Lost the bridge: ") + e.what());
        return 1;
    }

    // ---- commands ----
    msp::Commander commander(client, static_cast<int>(opts->timeout_s * 1000));
    msp::MotorTest motors(commander, opts->motors);
    if (!opts->cmd_log.empty() && !commander.open_log_file(opts->cmd_log)) {
        error("Cannot open the command log file " + opts->cmd_log);
        return 1;
    }
    if (opts->motors.enabled)
        commander.note("--enable-motors", msp::CommandRecord::Result::Info,
                       "motor test ON - PROPS OFF. limit " + std::to_string(opts->motors.max_value) +
                           ", auto-stop " + std::to_string(opts->motors.auto_stop_s) + " s");

    // ---- dashboard loop ----
    std::string failure;
    bool stopped_on_exit = false;
    {
        dash::Terminal term;
        dash::Dashboard board(dash::header_fields(motors), dash::sections());
        dash::CommandPanel panel;
        dash::InputLine input;
        std::vector<std::string> pending;   // typed commands, run between MSP requests

        auto refresh = [&] {
            term.write(board.update(telemetry));
            term.write(panel.update(commander.history(), commander.revision(), input));
        };
        auto redraw_all = [&] {
            const auto size = dash::Terminal::size();
            const int panel_rows = dash::CommandPanel::height_for(size.rows);
            term.write(board.layout(size.cols, size.rows - panel_rows));
            term.write(panel.layout(size.cols, size.rows - panel_rows + 1, panel_rows));
            refresh();
        };
        auto on_key = [&](int key) {
            if (input.editing) {
                if (key == 27) {                      // Esc (or an arrow key): cancel the line
                    while (term.read_key(0) != -1) {}
                    input = {};
                } else if (key == '\r' || key == '\n') {
                    if (!input.text.empty()) pending.push_back(input.text);
                    input = {};                        // back to normal mode: space is STOP again
                } else if (key == 127 || key == 8) {
                    if (!input.text.empty()) input.text.pop_back();
                } else if (key >= 32 && key < 127 && input.text.size() < 60) {
                    input.text += static_cast<char>(key);
                }
                return;
            }
            switch (key) {
                case 'q': case 'Q': g_stop = 1; break;
                case 'r': case 'R': g_resized = 1; break;
                case ':': case '\r': case '\n': input.editing = true; break;
                case ' ': pending.push_back("stop  (space)"); break;   // panic button
                default: break;
            }
        };
        auto handle_input = [&](int wait_ms) {
            for (int key = term.read_key(wait_ms); key != -1; key = term.read_key(0)) on_key(key);
            if (g_resized) {
                g_resized = 0;
                redraw_all();
            }
            for (const std::string& line : pending) dash::run_command(line, telemetry, commander, motors);
            pending.clear();
            motors.tick();
            refresh();
        };

        redraw_all();
        const auto period = std::chrono::duration<double>(1.0 / opts->rate_hz);
        try {
            while (!g_stop) {
                const auto start = std::chrono::steady_clock::now();
                poller.poll_cycle([&] {
                    handle_input(0);   // values appear as each reply lands; commands go out between requests
                    return !g_stop;
                });
                refresh();
                // Sleep out the rest of the period, still listening for keys.
                while (!g_stop) {
                    const auto left = period - (std::chrono::steady_clock::now() - start);
                    const auto left_ms = static_cast<int>(
                        std::chrono::duration_cast<std::chrono::milliseconds>(left).count());
                    if (left_ms <= 0) break;
                    handle_input(left_ms);
                }
            }
            // Never leave motors spinning behind us.
            if (motors.used()) {
                motors.stop("stop on exit");
                stopped_on_exit = true;
            }
        } catch (const msp::TransportError& e) {
            failure = e.what();
        }
    }  // terminal restored here

    if (!failure.empty()) {
        error("Lost the connection to the bridge: " + failure);
        if (motors.spinning())
            error("WARNING: the motors were last set to spin and could NOT be stopped.\n"
                  "Disconnect the battery.");
        return 1;
    }
    if (stopped_on_exit) std::fprintf(stderr, "Motors stopped.\n");
    std::fprintf(stderr, "Telemetry stopped.\n");
    return 0;
}
