import pytest
import subprocess
import logging
import yaml
import tempfile
import os

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

@dataclass
class CodeSample:
    endpoint: str
    method: str
    lang: str
    source: str

def extract_url_from_schema(schema_path):
    with open(schema_path, 'r') as f:
        schema = yaml.safe_load(f)    
    url = schema["servers"][0]["url"]
    if url[-1] != "/":
        url += "/"
    return url

    
def get_code_samples(schema_path):
    """Extract code samples from schema and group by language and method"""
    with open(schema_path, 'r') as f:
        schema = yaml.safe_load(f)
    samples = []
    for path, method_description in schema["paths"].items():
        for method, description in method_description.items():
            examples = description.get("x-code-samples", [])
            for example in examples:
                lang = example["lang"]
                source = example["source"]
                sample = CodeSample(endpoint=path, method=method, lang=lang, source=source)
                samples.append(sample)
    return samples


class SampleHandler:
    status_code_msg = None
    subprocess_args = None

    def __init__(self, base_url, sample, environment='production'):
        self.base_url = base_url
        self.sample = deepcopy(sample)
        self.environment = environment

    def change_api_key(self):
        self.sample.source = self.sample.source.replace('API_TEST_KEY', os.environ["API_TEST_KEY"])

    def add_status_code_message(self):
        self.sample.source = self.sample.source + self.status_code_msg

    def run(self):
        self.change_api_key()
        self.add_status_code_message()
        result = self.run_subprocess()
        return result

    def run_subprocess(self):
        _, path = tempfile.mkstemp(suffix=self.extension)
        with open(path, 'w') as f:
            f.write(self.sample.source)
        args = self.subprocess_args + [path]
        result = None
        try: 
            result = subprocess.run(args, capture_output=True, text=True, check=False)
        except:
            pass
        finally:
            os.remove(path)
        return result


class RHandler(SampleHandler):
    status_code_msg = '\nwrite(r$status_code, stderr())'
    subprocess_args = ['Rscript']
    extension = ".R"


class PythonHandler(SampleHandler):
    status_code_msg = '\nimport sys;sys.stderr.write(str(r.status_code))'
    subprocess_args = ['python']
    extension = ".py"


class ShellHandler(SampleHandler):
    status_code_msg = ' -s -o /dev/null -w "%{http_code}\\n" 1>&2'
    subprocess_args = ['/bin/sh']
    extension = ".sh"


def get_language_handler(lang):
    lang = lang.lower()
    if lang == 'python':
        return PythonHandler
    elif lang == 'r':
        return RHandler
    elif lang == 'shell':
        return ShellHandler
    else:
        raise Exception(f"No handler found for lang {lang}")

path = Path('./schema/schema.yaml')
samples = get_code_samples(schema_path=path)

@pytest.fixture
def base_url():
    url = os.environ.get("API_BASE_URL") or extract_url_from_schema(schema_path=path)
    return url

@pytest.mark.parametrize('sample', samples)
def test_code_sample(base_url, sample):
    handler = get_language_handler(sample.lang)
    h = handler(base_url=base_url, sample=sample)
    s = h.run()
    assert s.stderr.strip() == '200'


if __name__ == '__main__':
    samples = get_code_samples(schema_path=path)
    for sample in samples:
        test_code_sample(base_url=base_url, sample=sample)
