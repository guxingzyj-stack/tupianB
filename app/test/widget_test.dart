import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:laozhao/main.dart';

void main() {
  testWidgets('首页渲染标题和两个大方块', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: LaozhaoApp()));
    await tester.pumpAndSettle();

    expect(find.text('您想做什么？'), findsOneWidget);
    expect(find.text('修照片'), findsOneWidget);
    expect(find.text('做祝福'), findsOneWidget);
  });
}
