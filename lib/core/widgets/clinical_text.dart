import 'package:flutter/material.dart';

/// Layout-only parsing. Original clinical wording and citation tokens stay intact.
class ClinicalTextBlock {
  final String text;
  final bool bullet;
  final bool nested;
  final String marker;
  final bool heading;
  const ClinicalTextBlock(
    this.text, {
    this.bullet = false,
    this.nested = false,
    this.marker = '•',
    this.heading = false,
  });
}

List<ClinicalTextBlock> clinicalTextBlocks(String source) {
  var text = source.replaceAll('\r\n', '\n');
  for (final heading in [
    'Red flag clinical indicators:',
    'Other clinical indicators:',
  ]) {
    text = text.replaceAll(heading, '\n\n$heading');
  }
  text = text
      .replaceAllMapped(RegExp(r'[ \t]*[•●]\s*'), (_) => '\n• ')
      .replaceAllMapped(RegExp(r'[ \t]*－\s+'), (_) => '\n  - ');
  return [
    for (final line in text.split('\n'))
      if (line.trim().isNotEmpty) _block(line),
  ];
}

ClinicalTextBlock _block(String line) {
  final bullet = RegExp(r'^(\s*)(?:[•●*-]|\d+[.)])\s+').firstMatch(line);
  if (bullet != null) {
    return ClinicalTextBlock(
      line.substring(bullet.end).trim(),
      bullet: true,
      marker: RegExp(r'^\s*(\d+[.)])').firstMatch(line)?.group(1) ?? '•',
      nested: bullet.group(1)!.length >= 2,
    );
  }
  var text = line.trim();
  final heading =
      RegExp(r'^#{1,6}\s+').hasMatch(text) ||
      (text.endsWith(':') && text.length < 100) ||
      (text.startsWith('**') && text.endsWith('**'));
  text = text.replaceFirst(RegExp(r'^#{1,6}\s+'), '');
  return ClinicalTextBlock(text, heading: heading);
}

/// Used for narrative outputs without evidence links; citations use the same blocks.
class ClinicalText extends StatelessWidget {
  final String text;
  final TextStyle? style;
  const ClinicalText(this.text, {super.key, this.style});
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      for (final block in clinicalTextBlocks(text))
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (block.nested) const SizedBox(width: 14),
              if (block.bullet)
                Padding(
                  padding: const EdgeInsets.only(right: 9),
                  child: Text(block.marker),
                ),
              Expanded(
                child: Text.rich(
                  TextSpan(children: clinicalInlineSpans(block.text)),
                  style: (style ?? const TextStyle(fontSize: 15, height: 1.6))
                      .copyWith(
                        fontWeight: block.heading ? FontWeight.w700 : null,
                      ),
                ),
              ),
            ],
          ),
        ),
    ],
  );
}

List<TextSpan> clinicalInlineSpans(String text) {
  final matches = RegExp(r'\*\*(.+?)\*\*').allMatches(text);
  final spans = <TextSpan>[];
  var last = 0;
  for (final m in matches) {
    if (m.start > last) {
      spans.add(TextSpan(text: text.substring(last, m.start)));
    }
    spans.add(
      TextSpan(
        text: m.group(1),
        style: const TextStyle(fontWeight: FontWeight.w700),
      ),
    );
    last = m.end;
  }
  if (last < text.length) spans.add(TextSpan(text: text.substring(last)));
  // Labels such as "Blood culture:" are emphasized without changing the wording.
  if (spans.length == 1 && !text.startsWith('http')) {
    final colon = text.indexOf(':');
    if (colon > 0 && colon < 65) {
      return [
        TextSpan(
          text: text.substring(0, colon + 1),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        TextSpan(text: text.substring(colon + 1)),
      ];
    }
  }
  return spans;
}
