// ignore_for_file: deprecated_member_use, avoid_web_libraries_in_flutter
import 'dart:html' as html;
import 'package:flutter/foundation.dart';
import 'inline_audio.dart';

AppAudioPlayer getAudioPlayer() => WebAudioPlayer();

class WebAudioPlayer implements AppAudioPlayer {
  html.AudioElement? _element;
  bool _isPlaying = false;

  @override
  bool get isPlaying => _isPlaying;

  @override
  void play(String url, {VoidCallback? onEnded, VoidCallback? onError}) {
    stop();
    try {
      _element = html.AudioElement(url);
      _isPlaying = true;
      _element!.onEnded.listen((_) {
        _isPlaying = false;
        if (onEnded != null) onEnded();
      });
      _element!.onError.listen((_) {
        _isPlaying = false;
        if (onError != null) onError();
      });
      _element!.play();
    } catch (e) {
      _isPlaying = false;
      if (onError != null) onError();
    }
  }

  @override
  void pause() {
    _element?.pause();
    _isPlaying = false;
  }

  @override
  void stop() {
    if (_element != null) {
      _element!.pause();
      _element!.src = '';
      _element = null;
    }
    _isPlaying = false;
  }
}
