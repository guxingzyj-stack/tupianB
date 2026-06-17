import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:laozhao/features/history/storage/history_db.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

HistoryEntry _entry(String id, int createdAt, String name) => HistoryEntry(
      id: id,
      createdAt: createdAt,
      intentName: name,
      thumb: Uint8List.fromList([1, 2, 3, 4]),
    );

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  test('insert + recent 返回倒序', () async {
    final db = HistoryDb(pathOverride: inMemoryDatabasePath);
    addTearDown(db.close);
    final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;

    await db.insert(_entry('a', now - 100, '动物更清楚'));
    await db.insert(_entry('b', now - 10, '暖色草原'));

    final list = await db.recent();
    expect(list.length, 2);
    expect(list.first.id, 'b'); // 最新在前
    expect(list.first.intentName, '暖色草原');
    expect(list.first.thumb, isNotEmpty);
  });

  test('cleanup 删除 30 天前的, 保留近的', () async {
    final db = HistoryDb(pathOverride: inMemoryDatabasePath);
    addTearDown(db.close);
    final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;

    await db.insert(_entry('old', now - 40 * 86400, '旧'));
    await db.insert(_entry('fresh', now - 86400, '新'));

    final removed = await db.cleanup(days: 30);
    expect(removed, 1);

    final list = await db.recent();
    expect(list.length, 1);
    expect(list.first.id, 'fresh');
  });
}
