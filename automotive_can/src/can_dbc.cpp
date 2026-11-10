#include "automotive_can/can_dbc.hpp"

#include <cmath>
#include <regex>
#include <stdexcept>

namespace automotive_can {
namespace {
unsigned frame_limit(const CanFrame& f) { return f.format == FrameFormat::Classical ? 8U : 64U; }

std::uint64_t raw_value(const std::vector<std::uint8_t>& bytes, const Signal& s) {
  if (s.length == 0 || s.length > 64) throw std::invalid_argument("signal length must be 1..64");
  std::uint64_t raw = 0;
  if (s.order == ByteOrder::Intel) {
    for (unsigned i = 0; i < s.length; ++i) {
      const unsigned bit = s.start_bit + i;
      if ((bytes.at(bit / 8U) >> (bit % 8U)) & 1U) raw |= (std::uint64_t{1} << i);
    }
  } else {
    unsigned bit = s.start_bit;
    for (unsigned i = 0; i < s.length; ++i) {
      raw = (raw << 1U) | ((bytes.at(bit / 8U) >> (bit % 8U)) & 1U);
      bit = (bit % 8U == 0U) ? bit + 15U : bit - 1U;
    }
  }
  return raw;
}

double signed_value(std::uint64_t raw, unsigned length) {
  if (length == 64) return static_cast<double>(static_cast<std::int64_t>(raw));
  const auto sign = std::uint64_t{1} << (length - 1U);
  if (raw & sign) raw |= (~std::uint64_t{0} << length);
  return static_cast<double>(static_cast<std::int64_t>(raw));
}
}  // namespace

void Dbc::add_signal(Signal s) {
  if (s.length == 0 || s.length > 64) throw std::invalid_argument("signal length must be 1..64");
  messages_[s.message_id].push_back(std::move(s));
}

Dbc Dbc::parse(const std::string& text) {
  Dbc db;
  std::uint32_t current_id = 0;
  bool have_message = false;
  const std::regex msg(R"(^\s*BO_\s+(\d+)\s+[^:]+:\s+(\d+)\s+\S+)");
  const std::regex sig(R"DBC(^\s*SG_\s+(\w+)\s+(?:\w+\s+)?:\s*(\d+)\|(\d+)@(\d)([+-])\s*\(([-+0-9.eE]+),([-+0-9.eE]+)\)\s*\[([-+0-9.eE]+)\|([-+0-9.eE]+)\]\s*"([^"]*)")DBC");
  std::string line;
  std::size_t pos = 0;
  while (pos <= text.size()) {
    const auto end = text.find('\n', pos);
    line = text.substr(pos, end == std::string::npos ? std::string::npos : end - pos);
    std::smatch m;
    if (std::regex_search(line, m, msg)) {
      current_id = static_cast<std::uint32_t>(std::stoul(m[1]));
      have_message = true;
    } else if (std::regex_search(line, m, sig) && have_message) {
      Signal s;
      s.name = m[1]; s.message_id = current_id;
      s.start_bit = static_cast<unsigned>(std::stoul(m[2]));
      s.length = static_cast<unsigned>(std::stoul(m[3]));
      s.order = m[4] == "1" ? ByteOrder::Intel : ByteOrder::Motorola;
      s.is_signed = m[5] == "-";
      s.factor = std::stod(m[6]); s.offset = std::stod(m[7]);
      s.minimum = std::stod(m[8]); s.maximum = std::stod(m[9]); s.unit = m[10];
      db.add_signal(std::move(s));
    }
    if (end == std::string::npos) break;
    pos = end + 1;
  }
  return db;
}

std::map<std::string, DecodedSignal> Dbc::decode(const CanFrame& frame) const {
  if (frame.data.size() > frame_limit(frame)) throw std::invalid_argument("frame exceeds selected CAN format limit");
  std::map<std::string, DecodedSignal> out;
  const auto it = messages_.find(frame.id);
  if (it == messages_.end()) return out;
  for (const auto& s : it->second) {
    DecodedSignal d; d.timestamp_ns = frame.timestamp_ns;
    unsigned last = s.start_bit;
    if (s.order == ByteOrder::Intel) last += s.length - 1U;
    else for (unsigned i = 1; i < s.length; ++i) last = (last % 8U == 0U) ? last + 15U : last - 1U;
    if (last / 8U >= frame.data.size()) { d.reason = "signal exceeds frame payload"; out[s.name] = d; continue; }
    const auto bits = raw_value(frame.data, s);
    d.raw = s.is_signed ? signed_value(bits, s.length) : static_cast<double>(bits);
    d.physical = d.raw * s.factor + s.offset;
    d.valid = std::isfinite(d.physical) && d.physical >= s.minimum && d.physical <= s.maximum;
    if (!d.valid) d.reason = "physical value outside DBC range";
    out[s.name] = d;
  }
  return out;
}

VehicleState StateTracker::ingest(const CanFrame& frame, const Dbc& dbc) {
  if (drops_[frame.id]) { state_.faults.push_back("injected frame drop"); return state_; }
  if (frame.data.size() > frame_limit(frame)) { state_.faults.push_back("invalid CAN payload length"); return state_; }
  if (frame.timestamp_ns < last_timestamp_ns_) { state_.faults.push_back("out-of-order frame"); return state_; }
  auto decoded = dbc.decode(frame);
  if (decoded.empty()) { state_.faults.push_back("unmapped frame"); return state_; }
  last_timestamp_ns_ = frame.timestamp_ns;
  state_.timestamp_ns = frame.timestamp_ns;
  for (auto& entry : decoded) {
    if (!entry.second.valid) state_.faults.push_back("invalid signal: " + entry.first);
    state_.signals[entry.first] = entry.second;
    if (entry.second.valid) {
      if (entry.first == "VehicleSpeed") state_.speed_mps = entry.second.physical;
      else if (entry.first == "RoadFriction") state_.friction_coefficient = entry.second.physical;
      else if (entry.first == "MaxDecel") state_.max_decel_mps2 = entry.second.physical;
    }
  }
  state_.valid = true;
  for (const auto& entry : state_.signals) {
    if (!entry.second.valid || frame.timestamp_ns < entry.second.timestamp_ns ||
        frame.timestamp_ns - entry.second.timestamp_ns > stale_after_ns_) state_.valid = false;
  }
  return state_;
}

VehicleState StateTracker::snapshot(std::uint64_t now_ns) const {
  auto copy = state_;
  if (last_timestamp_ns_ == 0 || now_ns < last_timestamp_ns_ || now_ns - last_timestamp_ns_ > stale_after_ns_) {
    copy.valid = false; copy.faults.push_back("vehicle state stale or missing");
  }
  for (const auto& entry : copy.signals) {
    if (now_ns < entry.second.timestamp_ns || now_ns - entry.second.timestamp_ns > stale_after_ns_) {
      copy.valid = false; copy.faults.push_back("signal stale: " + entry.first);
    }
  }
  return copy;
}

void StateTracker::inject_drop(std::uint32_t id, bool enabled) { drops_[id] = enabled; }

}  // namespace automotive_can
