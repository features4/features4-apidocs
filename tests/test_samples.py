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
    base_url: str
    endpoint: str
    method: str
    lang: str
    source: str

def extract_url_from_schema(schema):
    url = schema["servers"][0]["url"]
    if url[-1] != "/":
        url += "/"
    return url

    
def get_code_samples(schema_path):
    """Extract code samples from schema and group by language and method"""
    with open(schema_path, 'r') as f:
        schema = yaml.safe_load(f)
    samples = []
    url = extract_url_from_schema(schema=schema)
    for path, method_description in schema["paths"].items():
        for method, description in method_description.items():
            examples = description.get("x-code-samples", [])
            for example in examples:
                lang = example["lang"]
                source = example["source"]
                sample = CodeSample(base_url=url, endpoint=path, method=method, lang=lang, source=source)
                samples.append(sample)
    return samples


class SampleHandler:
    status_code_msg = None
    subprocess_args = None

    def __init__(self, sample, base_url=None, api_key=None):
        self.sample = deepcopy(sample)
        if base_url and not base_url.endswith("/"):
            base_url += "/"
        self.base_url = base_url
        self.api_key = api_key

    def change_api_key(self):
        self.sample.source = self.sample.source.replace('API_TEST_KEY', self.api_key)

    def add_status_code_message(self):
        self.sample.source = self.sample.source + self.status_code_msg

    def replace_base_url(self, url):
        self.sample.source = self.sample.source.replace(self.sample.base_url, url)

    def run(self):
        if self.base_url:
            self.replace_base_url(url=self.base_url)
        if self.api_key:
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

@pytest.fixture
def api_key():
    key = os.environ.get("API_TEST_KEY")
    return key

@pytest.mark.parametrize('sample', samples)
def test_code_sample(sample, base_url=None, api_key=None):
    handler = get_language_handler(sample.lang)
    h = handler(sample=sample, base_url=base_url, api_key=api_key)
    s = h.run()
    assert s.stderr.strip() == '200'


if __name__ == '__main__':
    samples = get_code_samples(schema_path=path)
    for sample in samples:
        test_code_sample(sample=sample, base_url="http://localhost:8000/v1/")
