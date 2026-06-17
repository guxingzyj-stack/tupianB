import 'package:flutter/material.dart';

/// 长按显示原图, 松开恢复结果图 (PRD §3.3 原图对比)。
class LongPressCompareView extends StatefulWidget {
  final ImageProvider resultImage;
  final ImageProvider originalImage;
  final double aspectRatio;

  const LongPressCompareView({
    super.key,
    required this.resultImage,
    required this.originalImage,
    this.aspectRatio = 4 / 3,
  });

  @override
  State<LongPressCompareView> createState() => _LongPressCompareViewState();
}

class _LongPressCompareViewState extends State<LongPressCompareView> {
  bool _showOriginal = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onLongPressStart: (_) => setState(() => _showOriginal = true),
      onLongPressEnd: (_) => setState(() => _showOriginal = false),
      child: Stack(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: AspectRatio(
              aspectRatio: widget.aspectRatio,
              child: Image(
                image: _showOriginal ? widget.originalImage : widget.resultImage,
                fit: BoxFit.cover,
                gaplessPlayback: true,
              ),
            ),
          ),
          Positioned(
            top: 10,
            left: 10,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.55),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                _showOriginal ? '原来的样子' : '按住看原图',
                style: const TextStyle(color: Colors.white, fontSize: 15),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
