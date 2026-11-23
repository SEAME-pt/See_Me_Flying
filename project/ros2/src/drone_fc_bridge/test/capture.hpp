// Test helpers: hex strings and the capture files in test/data.

#ifndef CAPTURE_HPP_
#define CAPTURE_HPP_

#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

using Bytes = std::vector<uint8_t>;

inline const char * const CAPTURE_FILES[] = {"flat_still", "radio_off", "tilted", "flow_moving"};

inline Bytes from_hex(const std::string & hex)
{
  Bytes out;
  for (std::size_t i = 0; i + 1 < hex.size(); i += 2) {
    out.push_back(static_cast<uint8_t>(std::stoul(hex.substr(i, 2), nullptr, 16)));
  }
  return out;
}

struct CaptureLine
{
  int line{0};     // 1-based line in the file
  int cmd{0};
  bool ok{false};
  Bytes frame;     // empty when the request timed out
};

// The text after "key": up to the next comma, quote or brace. Enough for
// these files: they are flat and written by a script.
inline std::string json_value(const std::string & line, const std::string & key)
{
  const auto at = line.find("\"" + key + "\": ");
  if (at == std::string::npos) {
    return "";
  }
  auto start = at + key.size() + 4;
  if (line[start] == '"') {
    ++start;
  }
  return line.substr(start, line.find_first_of(",\"}", start) - start);
}

// Every request line of test/data/<name>.jsonl (the first line, the setup, is skipped).
inline std::vector<CaptureLine> load_capture(const std::string & name)
{
  const std::string path = std::string(TEST_DATA_DIR) + "/" + name + ".jsonl";
  std::ifstream in(path);
  if (!in) {
    throw std::runtime_error("cannot open " + path);
  }
  std::vector<CaptureLine> out;
  std::string text;
  for (int n = 1; std::getline(in, text); ++n) {
    if (json_value(text, "cmd").empty()) {
      continue;
    }
    CaptureLine l;
    l.line = n;
    l.cmd = std::stoi(json_value(text, "cmd"));
    l.ok = json_value(text, "ok") == "true";
    l.frame = from_hex(json_value(text, "hex"));
    out.push_back(l);
  }
  return out;
}

#endif  // CAPTURE_HPP_
