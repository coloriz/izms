import subprocess
import sys


def execute_handler(handler: str, *args) -> int:
    """
    핸들러를 실행하고 핸들러의 return code를 리턴하는 함수

    :param handler: 핸들러의 경로.
                    .py 파일일 경우 python interpreter 의 인자로 호출.
                    .sh 파일일 경우 /bin/sh 의 인자로 호출.
    :param args: 핸들러를 호출할 때 인자로 들어갈 인수 목록
    :return: 핸들러의 반환값
    """
    if handler.endswith('.py'):
        process = subprocess.run([sys.executable, handler] + list(args))
    elif handler.endswith('.sh'):
        process = subprocess.run(['/bin/sh', handler] + list(args))
    else:
        process = subprocess.run([handler] + list(args))

    return process.returncode
