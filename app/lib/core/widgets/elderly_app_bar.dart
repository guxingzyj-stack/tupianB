import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// 适老化顶栏: 大返回箭头 (触达≥56)、标题22+、无溢出菜单。
class ElderlyAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final List<Widget>? actions;

  const ElderlyAppBar({super.key, required this.title, this.actions});

  @override
  Size get preferredSize => const Size.fromHeight(64);

  @override
  Widget build(BuildContext context) {
    final canPop = context.canPop();
    return AppBar(
      automaticallyImplyLeading: false,
      toolbarHeight: 64,
      leading: canPop
          ? IconButton(
              icon: const Icon(Icons.arrow_back_ios_new, size: 28),
              constraints: const BoxConstraints(minWidth: 56, minHeight: 56),
              tooltip: '返回',
              onPressed: () => context.pop(),
            )
          : null,
      title: Text(title),
      actions: actions,
    );
  }
}
