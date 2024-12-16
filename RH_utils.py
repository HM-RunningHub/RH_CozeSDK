from runtime import Args
from typings.RH_util_getResult.RH_util_getResult import Input, Output
import requests
import json
import time


# 获取账户状态的函数，返回当前任务数量
# Function to get account status and return current task count
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
    
    # 发送POST请求，获取账户状态
    # Send POST request to get account status
    response = requests.post(url, headers=headers, json=data)
    
    # 解析响应数据
    # Parse response data
    if response.status_code == 200:
        response_json = response.json()
        if response_json.get('code') == 0:
            return response_json['data']['currentTaskCounts']
        else:
            return f"Error: {response_json.get('msg')}"
    else:
        return f"HTTP Error: {response.status_code}"


# 查询任务结果，若任务完成则返回文件URL
# Query task result, return file URL when task is completed
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

    # 每隔一定时间查询任务状态，直到任务完成或超时
    # Polling task status until it finishes or times out
    while time.time() - start_time < timeout:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("msg") == "success":
                # 返回生成的文件URL
                # Return the generated file URL
                return result["data"][0]["fileUrl"]
            else:
                # 等待一段时间后重新查询
                # Wait and poll again
                time.sleep(poll_interval)
        else:
            print("Request failed with status code:", response.status_code)
            break
    
    raise TimeoutError(f"Query timeout: Task ID {task_id} not completed within {timeout} seconds.")


# 创建任务，返回任务ID
# Create a task and return task ID
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

    # 发送请求创建任务
    # Send request to create a task
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            response_data = response.json()
            task_id = response_data.get("data", {}).get("taskId", "")
            
            # 如果任务ID存在，则返回任务ID
            # Return task ID if created successfully
            if task_id:
                return task_id
            else:
                print("Task creation failed: taskId not found.")
                return 0
        else:
            print(f"Request failed with status code: {response.status_code}")
            return 0
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return 0


# 任务处理函数，获取任务结果
# Task handler function to fetch task result
def handler(args: Args[Input]) -> Output:
    api_key = args.input.apiKey
    task_id = args.input.taskid
    
    # 如果task_id不是有效的，返回错误信息
    # Return error message if task_id is not valid
    if not task_id.isdigit() or len(task_id) != 19:
        return {"result_url": "taskid不是有效的"}  # Task ID is not valid
    
    # 如果task_id为0，表示查询次数过多，任务未完成
    # If task_id is 0, indicate that the task hasn't completed after many queries
    if task_id == 0:
        print(f"超过100次查询，任务仍未完成，退出。")
        return
    
    # 查询任务结果
    # Query task result
    try:
        result_url = query_task_result(task_id, api_key, timeout=30, poll_interval=2)
        print("任务完成，生成的图片URL为:", result_url)
        return {"result_url": result_url}
    except TimeoutError as e:
        print(e)
        return {"result_url": "任务超时未完成"}  # Task timed out
