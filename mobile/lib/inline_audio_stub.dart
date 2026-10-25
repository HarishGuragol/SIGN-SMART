import 'package:flutter/foundation.dart';
import 'inline_audio.dart';

AppAudioPlayer getAudioPlayer() => StubAudioPlayer();

class StubAudioPlayer implements AppAudioPlayer {
  @override
  bool get isPlaying => false;

  @override
  void play(String url, {VoidCallback? onEnded, VoidCallback? onError}) {}

  @override
  void pause() {}

  @override
  void stop() {}
}
