import 'dart:typed_data';

import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

/// 一条历史记录。thumb 存结果图的缩略图 JPEG 字节
/// (后端结果 URL 24h 过期, 所以必须本地存字节, 不存 URL)。
class HistoryEntry {
  final String id;
  final int createdAt; // unix 秒
  final String intentName; // 老人看得懂的那个名字
  final Uint8List thumb;

  const HistoryEntry({
    required this.id,
    required this.createdAt,
    required this.intentName,
    required this.thumb,
  });
}

/// 本地历史库 (sqflite)。移动端原生; 桌面/测试用 ffi (设置 databaseFactory)。
class HistoryDb {
  final String? pathOverride; // 测试传 inMemoryDatabasePath
  Database? _db;

  HistoryDb({this.pathOverride});

  Future<Database> _open() async {
    if (_db != null) return _db!;
    final path = pathOverride ?? p.join(await getDatabasesPath(), 'history.db');
    _db = await openDatabase(
      path,
      version: 1,
      onCreate: (db, _) => db.execute(
        'CREATE TABLE history('
        'id TEXT PRIMARY KEY, '
        'created_at INTEGER NOT NULL, '
        'intent_name TEXT, '
        'thumb BLOB NOT NULL)',
      ),
    );
    return _db!;
  }

  Future<void> insert(HistoryEntry e) async {
    final db = await _open();
    await db.insert(
      'history',
      {
        'id': e.id,
        'created_at': e.createdAt,
        'intent_name': e.intentName,
        'thumb': e.thumb,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<List<HistoryEntry>> recent({int days = 30}) async {
    final db = await _open();
    final since = DateTime.now().millisecondsSinceEpoch ~/ 1000 - days * 86400;
    final rows = await db.query(
      'history',
      where: 'created_at >= ?',
      whereArgs: [since],
      orderBy: 'created_at DESC',
    );
    return rows
        .map((r) => HistoryEntry(
              id: r['id'] as String,
              createdAt: r['created_at'] as int,
              intentName: (r['intent_name'] as String?) ?? '',
              thumb: r['thumb'] as Uint8List,
            ))
        .toList();
  }

  /// 删除 days 天前的记录 (字节随行一起删, 不用单独清文件)。返回删除条数。
  Future<int> cleanup({int days = 30}) async {
    final db = await _open();
    final cutoff = DateTime.now().millisecondsSinceEpoch ~/ 1000 - days * 86400;
    return db.delete('history', where: 'created_at < ?', whereArgs: [cutoff]);
  }

  Future<void> close() async {
    await _db?.close();
    _db = null;
  }
}
