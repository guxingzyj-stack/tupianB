import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/theme.dart';
import '../../../core/api/media_api.dart';
import '../../../core/widgets/elderly_app_bar.dart';

/// 做祝福 - 模板列表 (任务 5.4): 4 分类 tab + 大缩略图网格。
class TemplateListPage extends ConsumerWidget {
  const TemplateListPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(templatesProvider);
    return async.when(
      loading: () => const Scaffold(
        appBar: ElderlyAppBar(title: '做祝福'),
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => Scaffold(
        appBar: const ElderlyAppBar(title: '做祝福'),
        body: Center(
          child: Text('一时打不开，稍后再试',
              style: Theme.of(context).textTheme.titleMedium),
        ),
      ),
      data: (cats) => DefaultTabController(
        length: cats.length,
        child: Scaffold(
          appBar: AppBar(
            title: const Text('做祝福'),
            bottom: TabBar(
              isScrollable: true,
              labelStyle: const TextStyle(fontSize: 19, fontWeight: FontWeight.w700),
              unselectedLabelStyle: const TextStyle(fontSize: 18),
              tabs: [for (final c in cats) Tab(text: c.name)],
            ),
          ),
          body: TabBarView(
            children: [for (final c in cats) _grid(context, c.templates)],
          ),
        ),
      ),
    );
  }

  Widget _grid(BuildContext context, List<TemplateItem> items) {
    return GridView.count(
      crossAxisCount: 2,
      padding: const EdgeInsets.all(16),
      mainAxisSpacing: 14,
      crossAxisSpacing: 14,
      childAspectRatio: 0.95,
      children: [for (final t in items) _card(context, t)],
    );
  }

  Widget _card(BuildContext context, TemplateItem t) {
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: ElderlyTheme.tealGrad,
        borderRadius: BorderRadius.circular(ElderlyTheme.radius),
        boxShadow: ElderlyTheme.shadowCard,
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(ElderlyTheme.radius),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () => context.push('/template/apply', extra: t),
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 54,
                  height: 54,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.22),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.card_giftcard_rounded, size: 30, color: Colors.white),
                ),
                const SizedBox(height: 12),
                Text(t.name,
                    style: const TextStyle(
                        fontSize: 21, fontWeight: FontWeight.w700, color: Colors.white)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
