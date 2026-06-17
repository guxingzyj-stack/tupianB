import 'package:flutter/material.dart';

import '../../app/theme.dart';

class PickerOption {
  final String name;
  final ImageProvider? preview;
  const PickerOption(this.name, {this.preview});
}

/// 三选项卡片: 横向缩略图, 选中描边+高亮, 字号≥17 (PRD §3.3)。
class OptionPicker extends StatelessWidget {
  final List<PickerOption> options;
  final int selectedIndex;
  final ValueChanged<int> onSelect;

  const OptionPicker({
    super.key,
    required this.options,
    required this.selectedIndex,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (int i = 0; i < options.length; i++) ...[
          if (i > 0) const SizedBox(width: 12),
          Expanded(child: _card(context, i, primary)),
        ],
      ],
    );
  }

  Widget _card(BuildContext context, int i, Color primary) {
    final selected = i == selectedIndex;
    final o = options[i];
    return GestureDetector(
      onTap: () => onSelect(i),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        decoration: BoxDecoration(
          color: ElderlyTheme.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: selected ? primary : ElderlyTheme.line,
            width: selected ? 2.5 : 1.2,
          ),
          boxShadow: selected ? null : ElderlyTheme.shadowCard,
        ),
        padding: const EdgeInsets.all(7),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(11),
              child: AspectRatio(
                aspectRatio: 1,
                child: o.preview != null
                    ? Image(image: o.preview!, fit: BoxFit.cover, gaplessPlayback: true)
                    : Container(
                        color: ElderlyTheme.bg,
                        child: const Icon(Icons.image_outlined,
                            size: 30, color: ElderlyTheme.subtle),
                      ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              o.name,
              style: TextStyle(
                fontSize: 17,
                fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                color: selected ? primary : ElderlyTheme.ink,
              ),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 2),
          ],
        ),
      ),
    );
  }
}
