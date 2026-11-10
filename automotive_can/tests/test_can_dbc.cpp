#include "automotive_can/can_dbc.hpp"
#include <cassert>
#include <cmath>
#include <iostream>

using namespace automotive_can;
int main() {
  const auto db = Dbc::parse(R"(BO_ 256 VehicleState: 8 ECU
 SG_ VehicleSpeed : 0|16@1+ (0.01,0) [0|250] "m/s" ECU
 SG_ SignedAccel : 16|8@1- (0.1,0) [-12|12] "m/s2" ECU
 SG_ Motorola : 31|8@0+ (1,0) [0|255] "" ECU
)");
  CanFrame f{256, false, FrameFormat::Classical, 100, {0xD2,0x04,0xF6,0x5A,0,0,0,0}};
  const auto decoded = db.decode(f);
  assert(std::abs(decoded.at("VehicleSpeed").physical - 12.34) < 1e-9);
  assert(std::abs(decoded.at("SignedAccel").physical + 1.0) < 1e-9);
  assert(decoded.at("Motorola").physical == 0x5A);
  StateTracker tracker(50);
  assert(tracker.ingest(f, db).valid);
  assert(!tracker.snapshot(151).valid);
  f.timestamp_ns = 90;
  assert(tracker.ingest(f, db).faults.back() == "out-of-order frame");
  CanFrame fd{256, false, FrameFormat::CanFd, 200, std::vector<std::uint8_t>(12, 0)};
  assert(db.decode(fd).at("VehicleSpeed").valid);
  bool rejected = false;
  try { CanFrame bad{256, false, FrameFormat::Classical, 0, std::vector<std::uint8_t>(9)}; db.decode(bad); }
  catch (...) { rejected = true; }
  assert(rejected);
  std::cout << "automotive_can C++ tests passed\n";
}
