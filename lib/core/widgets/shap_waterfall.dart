import 'dart:math' as math;
import 'package:flutter/material.dart';

class ShapStep {
  final String label;
  final double start, end;
  final bool total;
  const ShapStep(this.label, this.start, this.end, {this.total = false});
  double get change => end - start;
}

List<ShapStep> shapWaterfallSteps(
  double baseline,
  double prediction,
  List<Map<String, dynamic>> contributions, {
  int maxFeatures = 6,
}) {
  final ordered = [...contributions]
    ..sort(
      (a, b) => (b['contribution'] as num).abs().compareTo(
        (a['contribution'] as num).abs(),
      ),
    );
  if (!baseline.isFinite ||
      !prediction.isFinite ||
      baseline < 0 ||
      baseline > 1 ||
      prediction < 0 ||
      prediction > 1 ||
      ordered.any((c) => !(c['contribution'] as num).isFinite)) {
    throw ArgumentError('SHAP values must be finite.');
  }
  final sum = ordered.fold<double>(
    baseline,
    (v, c) => v + (c['contribution'] as num).toDouble(),
  );
  if ((sum - prediction).abs() > 1e-5) {
    throw ArgumentError('SHAP values do not reconcile with this prediction.');
  }
  final steps = <ShapStep>[ShapStep('Reference', 0, baseline, total: true)];
  var current = baseline;
  for (final c in ordered.take(maxFeatures)) {
    final next = current + (c['contribution'] as num).toDouble();
    steps.add(ShapStep(c['feature'].toString(), current, next));
    current = next;
  }
  if (ordered.length > maxFeatures) {
    final rest = ordered
        .skip(maxFeatures)
        .fold<double>(0, (v, c) => v + (c['contribution'] as num).toDouble());
    steps.add(
      ShapStep(
        'Other ${ordered.length - maxFeatures} inputs',
        current,
        current + rest,
      ),
    );
  }
  steps.add(ShapStep('Model score', 0, prediction, total: true));
  return steps;
}

class ShapWaterfall extends StatelessWidget {
  final double baseline, prediction;
  final List<Map<String, dynamic>> contributions;
  const ShapWaterfall({
    super.key,
    required this.baseline,
    required this.prediction,
    required this.contributions,
  });
  @override
  Widget build(BuildContext context) {
    List<ShapStep> steps;
    try {
      steps = shapWaterfallSteps(baseline, prediction, contributions);
    } on ArgumentError {
      return const Text(
        'The explanation does not match this model score. Request a new explanation.',
      );
    }
    final low = steps.map((s) => math.min(s.start, s.end)).reduce(math.min);
    final high = steps.map((s) => math.max(s.start, s.end)).reduce(math.max);
    final padding = math.max(.002, (high - low) * .06);
    final min = low - padding, max = high + padding;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'How inputs change the score',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            const Wrap(
              spacing: 16,
              runSpacing: 4,
              children: [
                Text(
                  '↑ Raises score',
                  style: TextStyle(color: Color(0xFFB42318)),
                ),
                Text(
                  '↓ Lowers score',
                  style: TextStyle(color: Color(0xFF1D4ED8)),
                ),
              ],
            ),
            const SizedBox(height: 16),
            for (final s in steps)
              Semantics(
                label:
                    '${s.label}: ${(s.total ? s.end : s.change) * 100} ${s.total ? 'percent' : 'percentage points'}',
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 96,
                        child: Text(
                          s.label.replaceAll('_', ' '),
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: s.total
                                ? FontWeight.w700
                                : FontWeight.w500,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: SizedBox(
                          height: 34,
                          child: CustomPaint(
                            painter: _WaterfallBar(s, min, max),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      SizedBox(
                        width: 67,
                        child: Text(
                          s.total
                              ? _percent(s.end)
                              : '${s.change >= 0 ? '+' : ''}${(s.change * 100).toStringAsFixed(2)} pp',
                          textAlign: TextAlign.right,
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 10),
            Text(
              'Percent scale: ${(min * 100).toStringAsFixed(1)} to ${(max * 100).toStringAsFixed(1)}. Intermediate bars add score contributions; the final bar is the model score.',
              style: TextStyle(
                fontSize: 12,
                height: 1.5,
                color: Colors.grey.shade700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

String _percent(double value) => value > .999
    ? '>99.9%'
    : value < .001
    ? '<0.1%'
    : '${(value * 100).toStringAsFixed(1)}%';

class _WaterfallBar extends CustomPainter {
  final ShapStep step;
  final double min, max;
  _WaterfallBar(this.step, this.min, this.max);
  @override
  void paint(Canvas canvas, Size size) {
    double x(double value) => (value - min) / (max - min) * size.width;
    final grid = Paint()
      ..color = const Color(0xFFE2E8F0)
      ..strokeWidth = 1;
    for (final t in [min, (min + max) / 2, max]) {
      canvas.drawLine(Offset(x(t), 0), Offset(x(t), size.height), grid);
    }
    final color = step.total
        ? const Color(0xFF334E68)
        : step.change >= 0
        ? const Color(0xFFB42318)
        : const Color(0xFF1D4ED8);
    final left = math.min(x(step.start), x(step.end)),
        right = math.max(x(step.start), x(step.end));
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTRB(left, 7, math.max(left + 1, right), 27),
        const Radius.circular(3),
      ),
      Paint()..color = color,
    );
    if (!step.total) {
      canvas.drawLine(
        Offset(x(step.start), 0),
        Offset(x(step.start), 7),
        Paint()
          ..color = color
          ..strokeWidth = 1.5,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _WaterfallBar old) =>
      old.step != step || old.min != min || old.max != max;
}
