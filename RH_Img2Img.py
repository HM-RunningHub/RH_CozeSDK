from runtime import Args
from typings.RH_t2i.RH_t2i import Input, Output
import requests
import json
import time
import logging


def get_account_status(apikey):
    """
    获取账户状态
    - Returns current task count or error message.
    获取账户当前的任务数量，或者返回错误信息。
    """
    url = 'https://www.runninghub.cn/uc/openapi/accountStatus'
    headers = {
        'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Host': 'www.runninghub.cn',
        'Connection': 'keep-alive'
    }

    data = {
        'apikey': apikey
    }

    # 发送POST请求
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        response_json = response.json()
        if response_json.get('code') == 0:
            return response_json['data']['currentTaskCounts']
        else:
            return f"Error: {response_json.get('msg')}"
    else:
        return f"HTTP Error: {response.status_code}"


def query_task_result(task_id, api_key, timeout=600, poll_interval=5):
    """
    查询任务执行结果
    - Polls the task status until success or timeout.
    查询任务状态，直到成功或超时。
    """
    url = "https://www.runninghub.cn/task/openapi/outputs"
    headers = {
        'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Host': 'www.runninghub.cn',
        'Connection': 'keep-alive'
    }

    data = {
        "taskId": task_id,
        "apiKey": api_key
    }

    start_time = time.time()

    while time.time() - start_time < timeout:
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()

            if result.get("msg") == "success":
                # 返回结果中的文件URL
                file_url = result["data"][0]["fileUrl"]
                return file_url
            else:
                # 如果msg不是success，等待指定时间后再查询
                time.sleep(poll_interval)
        else:
            print("请求失败，状态码:", response.status_code)
            break

    raise TimeoutError(f"查询任务结果超时，任务ID: {task_id} 未能在{timeout}秒内完成。")


def create_task(workflow_id, api_key, node_info_list):
    """
    创建任务
    - Sends a request to create a task with specified workflow and node info.
    向API发送请求以创建任务，使用指定的工作流和节点信息。
    """
    url = "https://www.runninghub.cn/task/openapi/create"
    headers = {
        "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Host": "www.runninghub.cn",
        "Connection": "keep-alive"
    }

    data = {
        "workflowId": workflow_id,
        "apiKey": api_key,
        "nodeInfoList": node_info_list
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            response_data = response.json()
            task_id = response_data.get("data", {}).get("taskId", "")

            if task_id:
                print(f"任务创建成功，任务ID: {task_id}")
                return task_id
            else:
                print("任务创建失败：未找到任务ID。")
                return 0
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return 0
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return 0


def handler(args: Args[Input]) -> Output:
    """
    任务处理函数
    - Extracts input data, creates a task, and retrieves the result.
    提取输入数据，创建任务并获取任务结果。
    """
    api_key = args.input.apiKey  # 从args.input获取apiKey

    try:
        # 从args.input获取图像URL
        image_url = args.input.image_url
        logging.debug(f"收到的image_url: {image_url}")
    except Exception as e:
        error_message = f"处理image_url时出错: {image_url}, 错误信息: {str(e)}"
        print(error_message)  # 打印错误信息
        raise Exception(error_message)  # 抛出异常

    workflow_id = args.input.workflowId  # 从args.input获取workflowId
    node_info_list = [
        {
            "nodeId": "18",  # 节点ID
            "fieldName": "image",  # 字段名称
            "fieldValue": image_url  # 字段值
        }
    ]

    # 查询任务状态，最多重试100次
    max_retries = 100
    retries = 0
    current_task_status = get_account_status(api_key)

    while current_task_status != "0" and retries < max_retries:
        print(f"当前任务状态: {current_task_status}, 正在等待5秒后重新查询...")
        time.sleep(5)
        current_task_status = get_account_status(api_key)
        retries += 1

    if current_task_status != "0":
        print(f"超过100次查询，任务仍未完成，退出。")
        return

    print(f"任务状态已变为0，继续执行后续操作。")

    task_id = create_task(workflow_id, api_key, node_info_list)
    if task_id == 0:
        print(f"任务创建失败，退出。")
        return

    try:
        result_url = query_task_result(task_id, api_key)
        print("任务完成，生成的图片URL为:", result_url)
        return {"result_url": result_url}
    except TimeoutError as e:
        print(e)
