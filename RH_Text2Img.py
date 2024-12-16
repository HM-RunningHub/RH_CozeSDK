from runtime import Args
from typings.RH_t2i.RH_t2i import Input, Output
import requests
import json
import time
import logging


# 获取账户任务状态
# Function to get account status
def get_account_status(apikey):
    url = 'https://www.runninghub.cn/uc/openapi/accountStatus'
    headers = {
        'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Host': 'www.runninghub.cn',
        'Connection': 'keep-alive'
    }
    data = {'apikey': apikey}

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # 自动抛出HTTP异常
        result = response.json()

        if result.get('code') == 0:
            return result['data']['currentTaskCounts']
        else:
            return f"Error: {result.get('msg')}"
    except requests.exceptions.RequestException as e:
        return f"Request failed: {str(e)}"  # 请求失败错误信息


# 查询任务结果
# Function to query task result
def query_task_result(task_id, api_key, timeout=600, poll_interval=5):
    url = "https://www.runninghub.cn/task/openapi/outputs"
    headers = {
        'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'Host': 'www.runninghub.cn',
        'Connection': 'keep-alive'
    }
    data = {"taskId": task_id, "apiKey": api_key}

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()

            if result.get("msg") == "success":
                return result["data"][0]["fileUrl"]
            time.sleep(poll_interval)  # 等待5秒后重新查询
        except requests.exceptions.RequestException as e:
            raise TimeoutError(f"请求失败: {str(e)}")

    raise TimeoutError(f"查询任务结果超时，任务ID: {task_id} 未能在{timeout}秒内完成。")


# 创建任务
# Function to create a task
def create_task(workflow_id, api_key, node_info_list):
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
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        response_data = response.json()
        task_data = response_data.get("data", {})

        task_id = task_data.get("taskId")
        if task_id:
            logging.info(f"Task created successfully. Task ID: {task_id}")
            return task_id
        else:
            logging.error("Task creation failed: taskId not found.")
            return 0
    except requests.exceptions.RequestException as e:
        logging.error(f"Error occurred: {str(e)}")
        return 0


# 处理函数
# Handler function for task processing
def handler(args: Args[Input]) -> Output:
    # 从args.input获取输入数据
    # Extract input data from args
    workflow_id = args.input.workflowId
    api_key = args.input.apiKey
    image_url = args.input.image_url

    logging.debug(f"Received image_url: {image_url}")

    # 查询账户任务状态直到任务可用
    # Query account status until task is available
    retries = 0
    current_task_status = get_account_status(api_key)
    while current_task_status != "0" and retries < 100:
        logging.info(f"当前任务状态: {current_task_status}, 正在等待5秒后重新查询...")
        time.sleep(5)
        current_task_status = get_account_status(api_key)
        retries += 1

    if current_task_status != "0":
        logging.warning("超过100次查询，任务仍未完成，退出。")
        return

    logging.info("任务状态已变为0，继续执行后续操作。")

    # 创建任务
    # Create the task
    node_info_list = [{"nodeId": "18", "fieldName": "image", "fieldValue": image_url}]
    task_id = create_task(workflow_id, api_key, node_info_list)

    if task_id == 0:
        logging.error("任务创建失败，退出。")
        return

    # 查询任务结果
    # Query the result of the task
    try:
        result_url = query_task_result(task_id, api_key)
        logging.info(f"任务完成，生成的图片URL为: {result_url}")
        return {"result_url": result_url}
    except TimeoutError as e:
        logging.error(f"Error: {str(e)}")
        return {"error": str(e)}
