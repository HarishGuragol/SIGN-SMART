import 'package:flutter/foundation.dart';
import 'inline_audio_stub.dart'
    if (dart.library.html) 'inline_audio_web.dart';

abstract class AppAudioPlayer {
  factory AppAudioPlayer() => getAudioPlayer();
  void play(String url, {VoidCallback? onEnded, VoidCallback? onError});
  void pause();
  void stop();
  bool get isPlaying;
}
