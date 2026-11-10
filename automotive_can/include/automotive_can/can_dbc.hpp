#pragma once

#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace automotive_can {

enum class FrameFormat { Classical, CanFd };
enum class ByteOrder { Intel, Motorola };

struct CanFrame {
  std::uint32_t id{};
  bool extended{false};
  FrameFormat format{FrameFormat::Classical};
  std::uint64_t timestamp_ns{};
  std::vector<std::uint8_t> data;
};

struct Signal {
  std::string name;
  std::uint32_t message_id{};
  unsigned start_bit{};
  unsigned length{};
  ByteOrder order{ByteOrder::Intel};
  bool is_signed{false};
  double factor{1.0};
  double offset{0.0};
  double minimum{-1.0e300};
  double maximum{1.0e300};
  std::string unit;
};

struct DecodedSignal {
  double raw{};
  double physical{};
  std::uint64_t timestamp_ns{};
  bool valid{false};
  std::string reason;
};

class Dbc {
 public:
  static Dbc parse(const std::string& text);
  void add_signal(Signal signal);
  const std::map<std::uint32_t, std::vector<Signal>>& messages() const { return messages_; }
  std::map<std::string, DecodedSignal> decode(const CanFrame& frame) const;

 private:
  std::map<std::uint32_t, std::vector<Signal>> messages_;
};

struct VehicleState {
  std::uint64_t timestamp_ns{};
  std::map<std::string, DecodedSignal> signals;
  std::optional<double> speed_mps;
  std::optional<double> friction_coefficient;
  std::optional<double> max_decel_mps2;
  bool valid{false};
  std::vector<std::string> faults;
};

class StateTracker {
 public:
  explicit StateTracker(std::uint64_t stale_after_ns) : stale_after_ns_(stale_after_ns) {}
  VehicleState ingest(const CanFrame& frame, const Dbc& dbc);
  VehicleState snapshot(std::uint64_t now_ns) const;
  void inject_drop(std::uint32_t id, bool enabled);
 private:
  std::uint64_t stale_after_ns_;
  std::uint64_t last_timestamp_ns_{};
  VehicleState state_;
  std::map<std::uint32_t, bool> drops_;
};

}  // namespace automotive_can
