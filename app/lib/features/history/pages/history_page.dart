import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/widgets/elderly_app_bar.dart';
import '../storage/history_db.dart';
import '../storage/history_service.dart';

/// 历史记录 (PRD §10 / 任务 3.6): 本地存, 按日期分组, 大缩略图。
/// 绝不显示: 用了哪个 AI、花了多少钱、耗时。
class HistoryPage extends ConsumerWidget {
  const HistoryPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(historyListProvider);
    return Scaffold(
      appBar: const ElderlyAppBar(title: '我修过的照片'),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _empty(context, '一时打不开，稍后再看'),
        data: (list) =>
            list.isEmpty ? _empty(context, '还没有修过的照片') : _grouped(context, list),
      ),
    );
  }

  Widget _empty(BuildContext context, String msg) {
    final t = Theme.of(context).textTheme;
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.photo_library_outlined, size: 72, color: Colors.black38),
          const SizedBox(height: 16),
          Text(msg, style: t.titleMedium),
        ],
      ),
    );
  }

  Widget _grouped(BuildContext context, List<HistoryEntry> list) {
    final t = Theme.of(context).textTheme;
    final groups = <String, List<HistoryEntry>>{};
    for (final e in list) {
      groups.putIfAbsent(_bucket(e.createdAt), () => []).add(e);
    }
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        for (final g in groups.entries) ...[
          Padding(
            padding: const EdgeInsets.fromLTRB(4, 8, 4, 12),
            child: Text(g.key, style: t.titleMedium),
          ),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 14,
            crossAxisSpacing: 14,
            childAspectRatio: 0.82,
            children: [for (final h in g.value) _tile(context, h)],
          ),
          const SizedBox(height: 8),
        ],
      ],
    );
  }

  String _bucket(int createdAtSec) {
    final now = DateTime.now();
    final d = DateTime.fromMillisecondsSinceEpoch(createdAtSec * 1000);
    final today = DateTime(now.year, now.month, now.day);
    final that = DateTime(d.year, d.month, d.day);
    final diff = today.difference(that).inDays;
    if (diff <= 0) return '今天';
    if (diff == 1) return '昨天';
    if (diff < 7) return '$diff 天前';
    return '更早';
  }

  Widget _tile(BuildContext context, HistoryEntry h) {
    return GestureDetector(
      onTap: () => _view(context, h),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Image.memory(h.thumb, fit: BoxFit.cover),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            h.intentName,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w500),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  void _view(BuildContext context, HistoryEntry h) {
    showDialog<void>(
      context: context,
      builder: (_) => Dialog(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.memory(h.thumb, fit: BoxFit.contain),
              ),
              const SizedBox(height: 12),
              Text(h.intentName,
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => Navigator.pop(context),
                  style: ElevatedButton.styleFrom(minimumSize: const Size.fromHeight(54)),
                  child: const Text('关闭'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
