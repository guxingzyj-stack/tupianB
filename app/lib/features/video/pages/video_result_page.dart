import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:video_player/video_player.dart';

import '../../../core/widgets/big_button.dart';
import '../../../core/widgets/elderly_app_bar.dart';

/// 视频结果页 (任务 5.3): 自动循环播放 + "AI 生成"水印 + 发家人/保存/再做一个。
class VideoResultPage extends StatefulWidget {
  final String videoUrl;
  const VideoResultPage({super.key, required this.videoUrl});

  @override
  State<VideoResultPage> createState() => _VideoResultPageState();
}

class _VideoResultPageState extends State<VideoResultPage> {
  VideoPlayerController? _controller;
  bool _ready = false;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      final c = VideoPlayerController.networkUrl(Uri.parse(widget.videoUrl));
      await c.initialize();
      await c.setLooping(true);
      await c.play();
      if (mounted) {
        setState(() {
          _controller = c;
          _ready = true;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _ready = false);
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  void _todo(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg, style: const TextStyle(fontSize: 18))),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const ElderlyAppBar(title: '做好了'),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: Stack(
                  alignment: Alignment.bottomRight,
                  children: [
                    AspectRatio(
                      aspectRatio: (_ready && _controller != null)
                          ? _controller!.value.aspectRatio
                          : 4 / 3,
                      child: (_ready && _controller != null)
                          ? VideoPlayer(_controller!)
                          : Container(
                              color: Colors.black87,
                              child: const Center(
                                child: Icon(Icons.movie, size: 64, color: Colors.white54),
                              ),
                            ),
                    ),
                    Container(
                      margin: const EdgeInsets.all(8),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.5),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Text('AI 生成',
                          style: TextStyle(color: Colors.white, fontSize: 13)),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: BigButton(
                      text: '发家人',
                      icon: Icons.send,
                      onPressed: () => _todo('分享给家人（微信分享开发中）'),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: BigButton(
                      text: '保存',
                      icon: Icons.download,
                      isPrimary: false,
                      onPressed: () => _todo('保存到相册（开发中）'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              BigButton(
                text: '再做一个',
                icon: Icons.refresh,
                isPrimary: false,
                onPressed: () => context.go('/'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
