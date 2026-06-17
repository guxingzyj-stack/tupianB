import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image/image.dart' as img;

import '../../../core/api/api_client.dart';
import 'history_db.dart';

/// 把图片缩成缩略图 (长边 ≤maxEdge), 省存储。
Uint8List makeThumb(Uint8List src, {int maxEdge = 600}) {
  final im = img.decodeImage(src);
  if (im == null) return src;
  final landscape = im.width >= im.height;
  final resized = img.copyResize(
    im,
    width: landscape ? maxEdge : null,
    height: landscape ? null : maxEdge,
  );
  return Uint8List.fromList(img.encodeJpg(resized, quality: 80));
}

class HistoryService {
  final HistoryDb db;
  final Dio dio;
  HistoryService(this.db, this.dio);

  Future<void> saveResultBytes({
    required Uint8List resultBytes,
    required String intentName,
  }) async {
    await db.insert(HistoryEntry(
      id: '${DateTime.now().microsecondsSinceEpoch}',
      createdAt: DateTime.now().millisecondsSinceEpoch ~/ 1000,
      intentName: intentName,
      thumb: makeThumb(resultBytes),
    ));
  }

  /// 从结果 URL 下载并存历史。失败静默 (历史存不上不该影响主流程)。
  Future<void> saveFromUrl({
    required String url,
    required String intentName,
  }) async {
    try {
      final resp = await dio.get<List<int>>(
        url,
        options: Options(responseType: ResponseType.bytes),
      );
      final bytes = Uint8List.fromList(resp.data ?? const []);
      if (bytes.isNotEmpty) {
        await saveResultBytes(resultBytes: bytes, intentName: intentName);
      }
    } catch (_) {
      // 忽略
    }
  }
}

final historyDbProvider = Provider<HistoryDb>((ref) => HistoryDb());

final historyServiceProvider = Provider<HistoryService>(
  (ref) => HistoryService(ref.watch(historyDbProvider), ref.watch(dioProvider)),
);

/// 历史列表 (顺便清理 30 天前的)。
final historyListProvider = FutureProvider<List<HistoryEntry>>((ref) async {
  final db = ref.watch(historyDbProvider);
  await db.cleanup();
  return db.recent();
});
