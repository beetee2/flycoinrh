"""P00 real API → isolated full graph → JSON boundary; no model/API mocks."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from flytrap.lab.api import create_lab_app
from flytrap.lab.contracts import LabResult, MOTORS, SEEDS

pytestmark = [pytest.mark.real_model, pytest.mark.timeout(120)]
EVIDENCE = Path('artifacts/milestones/P00')


def payload(a, b):
    return dict(schema_version='flytrap-lab-request-1', a=a, b=b)


def checked_compare(client, a, b, name):
    response = client.post('/api/lab/compare', json=payload(a, b))
    assert response.status_code == 200, response.text
    result = LabResult.model_validate_json(response.content)
    data = result.model_dump()
    assert LabResult.model_validate_json(result.model_dump_json()) == result
    assert data['request'] == payload(a, b)
    assert data['fixture'] is False and data['cached'] is False
    assert data['identities']['model']['learning_enabled'] is False
    assert data['identities']['model']['neural_state_mode'] == 'windowed_reset'
    assert data['identities']['model']['calibration']['calibration_id'] == 'untrained-visual-v1'
    for side, pixels in [('A', a), ('B', b)]:
        assert data['identities']['input_sha256'][side] == hashlib.sha256(bytes(pixels)).hexdigest()
        for population, detail in data['retina'][side]['populations'].items():
            sampled = [pixels[i] for i in detail['pixel_indices']]
            assert detail['sampled_pixels_u8'] == sampled
            values = np.asarray(sampled, dtype=np.float32) / 255
            drive = values * 180 if population == 'L1' else (1-values) * 180 * 0.6
            assert np.array_equal(drive, detail['drive_hz'])
        assert data['retina'][side]['sampled_pixel_count'] == 137
    assert data['comparison']['same_seed_repeatable']
    assert len(data['samples']) == 9
    indexed = {(s['side'], s['seed']):s for s in data['samples']}
    for seed in SEEDS:
        for key in ('motor_rates_hz', 'statistics'):
            assert indexed['A', seed][key] == indexed['A_repeat', seed][key]
    for motor in MOTORS:
        summary = data['comparison']['motor_rates_hz'][motor]
        rates_a = [indexed['A', seed]['motor_rates_hz'][motor] for seed in SEEDS]
        rates_b = [indexed['B', seed]['motor_rates_hz'][motor] for seed in SEEDS]
        assert summary['a_mean'] == pytest.approx(np.mean(rates_a))
        assert summary['b_sd'] == pytest.approx(np.std(rates_b, ddof=1))
        assert summary['paired_deltas'] == [b-a for a,b in zip(rates_a,rates_b)]
    (EVIDENCE/'review'/f'{name}.json').write_text(json.dumps(data, indent=2)+'\n')
    return indexed, data


def test_real_api_repeatability_equal_brightness_same_image_and_input_isolation():
    a = [255 if i % 16 % 4 < 2 else 0 for i in range(256)]
    b = [255 if i // 16 % 4 < 2 else 0 for i in range(256)]
    with TestClient(create_lab_app(), base_url='http://127.0.0.1:8766') as client:
        original, comparison = checked_compare(client, a, b, 'equal-brightness')
        assert comparison['comparison']['equal_brightness']
        assert not comparison['comparison']['same_image']
        control, control_data = checked_compare(client, a, a, 'same-image-control')
        assert control_data['comparison']['same_image']
        for seed in SEEDS:
            for key in ('motor_rates_hz', 'statistics'):
                assert control['A',seed][key] == control['B',seed][key]
        changed, _ = checked_compare(client, a, [0]*256, 'input-isolation')
        for seed in SEEDS:
            for key in ('motor_rates_hz', 'statistics'):
                assert original['A',seed][key] == changed['A',seed][key]
                assert original['A',seed][key] == control['A',seed][key]
        assert client.get('/api/lab/status').json()['state'] == 'ready'
