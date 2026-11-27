// Byte transports for MSP: TCP (esp-link on the drone) or a serial port
// (e.g. the spare D1 Mini plugged into the Pi). Linux/POSIX only.
#pragma once

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>

namespace msp {

struct TransportError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

class Transport {
public:
    virtual ~Transport() = default;
    virtual void write_all(const uint8_t* data, size_t len) = 0;
    // Waits up to timeout_ms for data. Returns the number of bytes read, or 0 on
    // timeout or signal. Throws TransportError if the link is gone.
    virtual size_t read_some(uint8_t* buf, size_t cap, int timeout_ms) = 0;
    virtual std::string describe() const = 0;
};

class FdTransport : public Transport {
public:
    ~FdTransport() override;
    FdTransport(const FdTransport&) = delete;
    FdTransport& operator=(const FdTransport&) = delete;

    void write_all(const uint8_t* data, size_t len) override;
    size_t read_some(uint8_t* buf, size_t cap, int timeout_ms) override;
    std::string describe() const override { return desc_; }
    int fd() const { return fd_; }   // for poll()-based event loops (the gateway)

protected:
    FdTransport() = default;
    int fd_ = -1;
    std::string desc_;
};

class TcpTransport : public FdTransport {
public:
    TcpTransport(const std::string& host, uint16_t port, int connect_timeout_ms = 5000);
};

class SerialTransport : public FdTransport {
public:
    SerialTransport(const std::string& device, int baud);
};

}  // namespace msp
