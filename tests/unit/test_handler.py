import io
import json
import toml
import boto3
import pytest

from term_search import app

with open('samconfig.toml', 'r') as f:
    config = toml.load(f)
    s3_bucket = config['default']['deploy']['parameters']['s3_bucket']
    s3_region = config['default']['deploy']['parameters']['region']


s3 = boto3.client('s3')


def get_s3_match_json(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(response['Body'].read())


def build_lambda_input(bucket, infile_json):

    return {
        "statusCode": 200,
        "body": {
            "message": "hello world",
            "bucket": bucket,
            # "orig": "raw/mn-sherburne-county/batch3/R3Part2/Abstract 88291.jpg",
            "json": infile_json,
            # "txt": "ocr/txt/mn-sherburne-county/batch3/R3Part2/Abstract 88291.txt",
            # "stats": "ocr/stats/mn-sherburne-county/batch3/R3Part2/Abstract 88291__69727524d8d04bfc99ee0f0bf22584e0.json",
            "uuid": "69727524d8d04bfc99ee0f0bf22584e0",
            # "handwriting_pct": 0.01
        }
    }

@pytest.fixture()
def death_cert_table_input_1():
    """ Generates API GW Event"""
    return build_lambda_input(s3_bucket, "ocr/json/mn-sherburne-county/RECEXPORT/Abstract 103872_SPLITPAGE_2.json")


def test_term_basic():
    # Trues
    assert app.test_match('caucasian', 'caucasian') == True
    assert app.test_match('caucasian', 'cau-casian') == True
    assert app.test_match('caucasian', 'caucasion') == True
    assert app.test_match('caucasian', 'cau-casion') == True
    assert app.test_match('caucasian', 'cauca-sion') == True
    assert app.test_match('caucasian', 'caucausian') == True
    assert app.test_match('caucasian', 'caucasin') == True
    assert app.test_match('caucasian', 'aucasian') == True
    assert app.test_match('caucasian', 'caboasian') == True
    assert app.test_match('caucasian', 'can-casia') == True
    assert app.test_match('caucasian', 'cancasian') == True
    assert app.test_match('caucasian', 'capcasian') == True
    assert app.test_match('caucasian', 'caticasian') == True
    assert app.test_match('caucasian', 'cau casian') == True
    assert app.test_match('caucasian', 'cauc- asia') == True
    assert app.test_match('caucasian', 'caucã¡sian') == True
    assert app.test_match('caucasian', 'caucagian') == True
    assert app.test_match('caucasian', 'caucaison') == True
    assert app.test_match('caucasian', 'caucasia') == True
    assert app.test_match('caucasian', 'caucasiã¡n') == True
    assert app.test_match('caucasian', 'caucasiã¤n') == True
    assert app.test_match('caucasian', 'caucasiar') == True
    assert app.test_match('caucasian', 'caucasiari') == True
    assert app.test_match('caucasian', 'caucasien') == True
    assert app.test_match('caucasian', 'caucasioan') == True
    assert app.test_match('caucasian', 'caucasisian') == True
    assert app.test_match('caucasian', 'caucasism') == True
    assert app.test_match('caucasian', 'caucassian') == True
    assert app.test_match('caucasian', 'caucastan') == True
    assert app.test_match('caucasian', 'caucastian') == True
    assert app.test_match('caucasian', 'cauccasian') == True
    assert app.test_match('caucasian', 'cauccian') == True
    assert app.test_match('caucasian', 'caucesian') == True
    assert app.test_match('caucasian', 'caudasian') == True
    assert app.test_match('caucasian', 'caueasian') == True
    assert app.test_match('caucasian', 'caugasian') == True
    assert app.test_match('caucasian', 'cauoasian') == True
    assert app.test_match('caucasian', 'causas ian') == True
    assert app.test_match('caucasian', 'causcasian') == True
    assert app.test_match('caucasian', 'caussian') == True
    assert app.test_match('caucasian', 'concasion') == True
    # assert app.test_match('caucasian', 'concession') == True
    assert app.test_match('caucasian', 'coucasion') == True
    assert app.test_match('caucasian', 'daucasi') == True
    assert app.test_match('caucasian', 'daucasian') == True
    assert app.test_match('caucasian', 'daucasion') == True
    # assert app.test_match('caucasian', 'gaucas') == True
    assert app.test_match('caucasian', 'gaucasian') == True
    assert app.test_match('caucasian', 'gaucasion') == True
    assert app.test_match('caucasian', 'saucasian') == True
    assert app.test_match('caucasian', 'vaucasian') == True

    # assert app.test_match('caucasian race', 'cã¡ugasiah rage') == True
    assert app.test_match('caucasian race', 'gaucasian cage') == True
    assert app.test_match('caucasian race', 'caueasien rage') == True

    # Falses
    assert app.test_match(' aryan', 'Maryanne') == False


def test_death_cert_table_input_1(death_cert_table_input_1):

    ret = app.lambda_handler(death_cert_table_input_1, "")
    data = ret["body"]
    print(data)

    assert ret["statusCode"] == 200
    assert "message" in ret["body"]
    assert data["message"] == "hello world"
    
    assert data["bool_hit"] == True
    assert data["match_file"] != None

    hit_json = get_s3_match_json(s3_bucket, data["match_file"])

    assert len(hit_json['date of death']) > 0
    assert len(hit_json['name of deceased']) > 0
