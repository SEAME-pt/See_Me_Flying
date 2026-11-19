// Puts the terminal into dashboard mode (alternate screen, hidden cursor,
// single-key input) and restores it on destruction.
#pragma once

#include <string>
#include <termios.h>

namespace dash {

class Terminal {
public:
    Terminal();
    ~Terminal();
    Terminal(const Terminal&) = delete;
    Terminal& operator=(const Terminal&) = delete;

    struct Size { int cols, rows; };
    static Size size();

    // Waits up to timeout_ms for a key; returns it, or -1 if none.
    int read_key(int timeout_ms);
    void write(const std::string& s);

private:
    termios saved_{};
    bool restore_ = false;
};

}  // namespace dash
