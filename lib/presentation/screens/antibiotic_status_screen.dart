import 'package:flutter/material.dart';
import '../../domain/eoscal_calculator.dart';

/// An absent automated plan never implies antibiotics are unnecessary.
class AntibioticStatusScreen extends StatelessWidget {
  final PatientParameters patient;
  final String activeGuideline;
  const AntibioticStatusScreen({
    super.key,
    required this.patient,
    required this.activeGuideline,
  });
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      Align(
        alignment: Alignment.centerLeft,
        child: Chip(label: Text(activeGuideline)),
      ),
      const Card(
        child: ListTile(
          title: Text('Medication decision requires clinician review'),
          subtitle: Text(
            'This app does not issue medication orders. Verify the prescription chart, clinical assessment, cultures, renal function and approved local neonatal pathway.',
          ),
        ),
      ),
      if (patient.bloodCulturePositive == true)
        const Card(
          child: ListTile(
            leading: Icon(Icons.warning_amber),
            title: Text('Positive culture recorded'),
            subtitle: Text(
              'Promptly verify the organism, susceptibility and clinical significance with the treating team.',
            ),
          ),
        ),
    ],
  );
}
