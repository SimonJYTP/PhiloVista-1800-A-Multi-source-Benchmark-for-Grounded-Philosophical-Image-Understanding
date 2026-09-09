-- Report snapshot queries. Inputs are independently recomputed audit outputs.
SELECT files, archive, synthetic, gold FROM metrics;
SELECT source, selected, local_byte_match, official_crosscheck, confidence FROM source_provenance;
SELECT check_name, passed, total, result FROM structural_checks;
SELECT metric, count, share, interpretation FROM qa_status;
SELECT source, revise, total, revise_share FROM qa_by_source ORDER BY revise_share DESC;
SELECT severity, sample_id, field_name, finding, recommended_fix FROM confirmed_findings;
