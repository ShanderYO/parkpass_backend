from typing import Optional

import docker


def is_container_running(container_name: str) -> Optional[bool]:
    """Verify the status of a container by it's name

    :param container_name: the name of the container
    :return: boolean or None
    """
    RUNNING = "running"
    # Connect to Docker using the default socket or the configuration
    # in your environment
    docker_client = docker.from_env()
    # Or give configuration
    # docker_socket = "unix://var/run/docker.sock"
    # docker_client = docker.DockerClient(docker_socket)

    try:
        container = docker_client.containers.get(container_name)
    except docker.errors.NotFound as exc:
        print(f"Check container name!\n{exc.explanation}")
    else:
        container_state = container.attrs["State"]
        return container_state["Status"] == RUNNING


def send_email(user, pwd, recipient, subject, body):
    import smtplib
    from email.mime.text import MIMEText
    from email.header import Header
    from email.parser import Parser

    from email.message import EmailMessage

    TO = recipient if isinstance(recipient, list) else [recipient]

    em = EmailMessage()
    em.set_content(body)
    em['To'] = TO
    em['From'] = user
    em['Subject'] = subject


    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(user, pwd)
        server.send_message(em)
        server.close()
        print('successfully sent the mail')
    except Exception as e:
        print("failed to send mail")
        print(e)

if __name__ == "__main__":
    container_names = ['celery-beat', 'celery-worker', 'user-landing-container', 'nginx-balancer', 'backend-master', 'owner-cabinet-container',
                       'user-cabinet-container', 'parkpass-postgres', 'vendor-landing-container', 'owner-landing-container',
                       'payment-container', 'parkpass_redis_1'
                       ]
    not_running_containers = []
    for container_name in container_names:
        if not is_container_running(container_name):
            not_running_containers.append(container_name)

    if not_running_containers:
        send_email(
            'noreply@parkpass.ru',
            'noreplyParol',
            ['lokkomokko1@gmail.com', 'app@vldmrnine.com'],
            '!!!! ОПОВЕЩЕНИЕ С САЙТА. ОТКЛЮЧИЛСЯ(-ЛИСЬ) КОНТЕЙНЕРЫ !!!!',
            'Список отключившихся контейнеров: ' + ', '.join(not_running_containers)
        )
