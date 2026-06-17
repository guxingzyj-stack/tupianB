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
      behavior: HitTestBehavior.opaque, // 整块区域都可点, 不漏手势
      // 点一下切换 (适老化, 比长按稳且好发现); 按住也支持: 按住看原图、松开恢复。
      onTap: () => setState(() => _showOriginal = !_showOriginal),
      onLongPressStart: (_) => setState(() => _showOriginal = true),
      onLongPressEnd: (_) => setState(() => _showOriginal = false),
      onLongPressCancel: () => setState(() => _showOriginal = false),
      child: Stack(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: AspectRatio(
              aspectRatio: widget.aspectRatio,
              // 原图与结果图都预先渲染, 用透明度瞬间切换 (避免重新加载导致"没反应")。
              child: Stack(
                fit: StackFit.expand,
                children: [
                  Image(image: widget.resultImage, fit: BoxFit.cover, gaplessPlayback: true),
                  Opacity(
                    opacity: _showOriginal ? 1.0 : 0.0,
                    child: Image(
                      image: widget.originalImage,
                      fit: BoxFit.cover,
                      gaplessPlayback: true,
                    ),
                  ),
                ],
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
                _showOriginal ? '这是原图 · 再点看修好的' : '点一下看原图',
                style: const TextStyle(color: Colors.white, fontSize: 15),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
