// Does AVFoundation (QuickTime's engine) accept the file?   usage: swift playable.swift FILE
import AVFoundation
let a = AVURLAsset(url: URL(fileURLWithPath: CommandLine.arguments[1]))
let s = DispatchSemaphore(value: 0)
Task { print("playable:", try await a.load(.isPlayable)); s.signal() }
s.wait()
