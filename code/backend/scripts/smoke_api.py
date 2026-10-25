"""Check a running local API without needing or inventing model predictions."""
import json
import urllib.request
import urllib.error
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    with urllib.request.urlopen(args.base_url + '/api/health', timeout=10) as response:
        health = json.load(response)
    assert health['device'] == 'cpu'
    assert health['calibration'] == 'none'
    assert health['prediction_task'] == 'overall_static_valence_arousal'
    print(json.dumps(health, ensure_ascii=True, indent=2))
    if health['status'] == 'not_ready':
        boundary = 'music-smoke-boundary'
        content = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="test.wav"\r\nContent-Type: audio/wav\r\n\r\n').encode() + b'no fake prediction' + (f'\r\n--{boundary}--\r\n').encode()
        request = urllib.request.Request(args.base_url + '/api/jobs', content,
                                         headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
        try:
            urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error:
            assert error.code == 503
            print('PASS: missing model rejects upload with HTTP 503')
        else:
            raise AssertionError('Missing model unexpectedly accepted inference')
    print('LOCAL_API_SMOKE_PASS; not an actual MERT audio prediction')


if __name__ == '__main__':
    main()
