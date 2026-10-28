# Final Demonstration Guide

1. Start WSL2 Ubuntu with Open vSwitch running.
2. Enter the project:
   `cd /mnt/c/Users/subiw/MEDROUTE_FINAL_GOD_HELP/MedRoute-Fresh`
3. Activate the Ryu environment:
   `export PATH="$HOME/.venvs/medroute-ryu/bin:$PATH"`
4. Run the live coordinator as root using the command in `README.md`.
5. Generate Stage 6 artifacts with `python3 scripts/generate_stage6.py <run>`.
6. Build the evidence index with `python3 scripts/build_evidence_db.py <run>`.
7. Start the dashboard with `npm run dashboard` from a shell that has Node.
8. Select the final run and show:
   - harmful shortcut decision
   - baseline route restoration
   - OpenFlow flow dumps
   - critical-class queue results
   - failure recovery
   - the consolidated executive summary and six-profile matrix
   - plots and confidence intervals
9. Verify `src/scenario_validation.js` returns `passed: true`.

Never present analytical output as live evidence, and never describe synthetic
criticality as a clinical decision.
