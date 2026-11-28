#!/bin/bash
set +x
CR=/data/var/b-batch/code5/xrg-batch
IMG=xrg-load-candidate@sha256:2af4d79666d168c2526fed2427dc7e5751872693a43a66272496264f989c8c58
export XNG_LOAD_PASSWORD="$(cat /run/secrets/xrg_loader_password)"
# host network + pg32b->127.0.0.1 is the proven-reachable construction; gates verify
# SERVER-side facts (SHOW port / inet_server_addr / marker), not client DNS.
docker run --rm -i --network host --add-host pg32b:127.0.0.1 \
  -v /opt/mydocker/xiangrugu/data/var:/data/var:rw \
  -v /run/secrets:/secrets:ro \
  -w "$CR" \
  -e PYTHONPATH="$CR/datamgmt/src" \
  --entrypoint sh "$IMG" -c '
    set +x
    export XNG_LOAD_PASSWORD="$(cat /secrets/xrg_loader_password)"
    python3 -m xiangrugu_datamgmt.cbdb_social_addr_runner \
      --phase phase2-production --code-root "'"$CR"'" \
      --code-commit a5d12b13ad87b74fea5e8e7b2fb8a2c901bbad9e \
      --contract "datamgmt/contracts/releases/2026-10-06-bootstrap/b-single-table-frozen-candidate.json" \
      --approval-table "datamgmt/contracts/releases/2026-10-06-bootstrap/b-approval-table-v2.json" \
      --approval-text ".b-batch-real-load-20261127/approval-text-verbatim.txt" \
      --approval-text-sha256 4d250c8e08ea8136e29e35aa436812f11b5eec59a100847f130c11f39b7e2946 \
      --scope ".b-batch-real-runner-binding-20261127/formal-scope.json" \
      --expected ".b-batch-real-runner-binding-20261127/formal-expected.runcopy.json" \
      --payload "/data/var/b-batch/payload.bin" \
      --scratch "/data/var/b-batch" \
      --evidence-out "/data/var/b-batch/evidence-formal-run.json" </dev/null
    RC=$?; echo "INNER_EXIT=$RC"; unset XNG_LOAD_PASSWORD; exit $RC'
RC=$?
echo "LOAD_EXIT=$RC"
unset XNG_LOAD_PASSWORD
exit "$RC"
