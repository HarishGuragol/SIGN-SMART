import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/main.dart';

void main() {
  testWidgets('SignSmartApp loads and displays brand', (WidgetTester tester) async {
    await tester.pumpWidget(const SignSmartApp());
    expect(find.text('SignSmart'), findsOneWidget);
    expect(find.text('AI Agreement Auditor & Law Evaluator'), findsOneWidget);
    await tester.pump(const Duration(seconds: 3));
    await tester.pumpAndSettle();
  });
}
