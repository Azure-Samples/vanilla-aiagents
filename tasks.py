from invoke import task, run

@task
def build(c, version: str):
    c.run(f"cd vanilla_aiagents && python setup.py sdist bdist_wheel --version {version}")

@task
def test(c, test_path: str = "vanilla_aiagents/tests/", test_case: str = ""):
    test_case_option = f"-k {test_case}" if test_case else ""
    coverage_option = f"--cov-append" if test_case else ""
    
    # Run tests with coverage
    c.run(f"pytest --cov=vanilla_aiagents --cov-report=term-missing --cov-report=html {coverage_option} --cov-config=.coveragerc {test_case_option} {test_path}")
        
    # Generate the combined coverage report
    c.run("coverage html")
    c.run("coverage xml")
    c.run("python vanilla_aiagents/tests/generate_coverage_badge.py")

    
@task
def build_grpc(c):
    proto_path = "vanilla_aiagents/vanilla_aiagents/remote"
    proto_file = f"{proto_path}/remote.proto"
    c.run(f"python -m grpc_tools.protoc -I{proto_path} --python_out={proto_path} --grpc_python_out={proto_path} {proto_file}")
    # Replace the import in remote_pb2_grpc.py
    # c.run("sed -i 's/from vanilla_aiagents.vanilla_aiagents.remote import remote_pb2/from vanilla_aiagents.remote import remote_pb2/' vanilla_aiagents/vanilla_aiagents/remote/remote_pb2_grpc.py")
    
@task
def docs(c):
    c.run("cd vanilla_aiagents && pdoc --output-dir docs -d markdown vanilla_aiagents !vanilla_aiagents.remote.grpc")
    
@task
def check_lint(c):
    c.run("cd vanilla_aiagents && flake8 vanilla_aiagents/")

@task
def check_docs(c):
    c.run("cd vanilla_aiagents && pydocstyle vanilla_aiagents/")

@task
def lint(c):
    c.run("cd vanilla_aiagents && black vanilla_aiagents/")    
    c.run("cd vanilla_aiagents && docformatter -i -r -s pep257 --black vanilla_aiagents/")