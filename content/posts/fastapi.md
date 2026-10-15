---
title: "FastAPI源码解析"
date: 2026-09-20
tags: ["FastAPI","Python"]
categories: ["技术"]
draft: true
---

# 请求解析和依赖注入流程

>如果有middleware，首先是从middleware开始处理
>ASGIApp = Callable\[\[Scope, Receive, Send], Awaitable\[None]]
>ASGIApp的类型是可调用的函数，接收三个参数：Scope，Receive，Send。返回的类型是可await的协程函数（async def定义），并且该函数执行完成后的返回值为None

涉及的主要方法：
`request_response` -> `get_request_handler` -> `solve_dependencies`

## 中间件处理

从starlette的`BaseHTTPMiddleware`到`ExceptionMiddleware`，再到FastAPI的`AsyncExitStackMiddleware`。
传递app（ASGIApp类型，是`fastapi.applications.FastAPI`实例对象）和conn（Request类型或WebSocket类型，请求信息）来初始化中间件middleware，然后在上述中间件的app运行方法中传递三个参数：
 - scope：字典类型，包含：
    - 堆栈调用信息（fastapi_middleware_astack、fastapi_inner_astack、
    - 请求方法信息（method，route，endpoint，path_params，scheme，path、header等）
 - receive：可调用的函数
 - send：可调用的函数
```python
from collections.abc import Awaitable, Callable, Mapping, MutableMapping
from typing import Any

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]

Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
```
创建stack（AsyncExitStack类型），将其存入scope中，在后续的处理中进行入栈出栈操作，用于在请求结束或依赖关闭后关闭文件
## 路由定位及堆栈初始化
从`AsyncExitStackMiddleware`调用`__call__`方法，跳转到FastAPI的`APIRouter`类（继承了starlette的Router类），调用类中实现的app方法
- 遍历所有路由（self.routes，APIRoute类型），找到与当前路由匹配的子路由及child_scope
- 用child_scope的内容更新scope，执行route的handle方法
- route对象继承自starlette的`Routing.Route`类，在handle方法中会通过`await super().handle(scope, receive, send)`调用starlette.Routing.Route类的handle方法，再通过`await self.app(scope, receive, send)`调用app方法
- 由于子类APIRoute中定义的self.app都是`self.app = request_response(self.get_route_handler())`，**因此会调用FastAPI中的`request_response`方法**
- 在`request_response`方法定义的app方法中，会**按顺序**初始化请求级别和函数级别的`AsyncExitStack`并加入到scope中
	- 请求级别：fastapi_inner_astack（request_stack）
	- 函数级别：fastapi_function_astack（function_stack）
	```python
		async with AsyncExitStack() as request_stack:
			scope["fastapi_inner_astack"] = request_stack
			async with AsyncExitStack() as function_stack:
				scope["fastapi_function_astack"] = function_stack
				# 这里的f是get_request_handler函数
				response = await f(request)
			await response(scope, receive, send)
	```


## 请求处理
在APIRoute类中定义`self.app = request_response(self.get_route_handler())`时，传入的参数`self.get_route_handler()`的返回值是`get_request_handler`方法的返回值（即ASGIApp类型的app函数）
```python
def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
	return get_request_handler(
		dependant=route.dependant,
		body_field=route.body_field,
		...
	)
```

```python
def get_request_handler(
    dependant: Dependant,
    body_field: ModelField | None = None,
    ...
) -> Callable[[Request], Coroutine[Any, Any, Response]]:
    assert dependant.call is not None, "dependant.call must be a function"

    async def app(request: Request) -> Response:
        response: Response | None = None
        file_stack = request.scope.get("fastapi_middleware_astack")
        ...
        # Return response
        assert response
        return response

    return app
```

`get_request_handler`方法的主要处理逻辑如下：
- 检查函数的endpoint函数是否存在，不存在则报错返回（这里的endpoint方法是作为dependant传入的，使用dependant.call查看）
- 检查endpoint函数（dependant.call）是否是协程函数，is_coroutine
- 还会检查是否是body_form, sse_stream等
- 在app方法中，
	- 先获取到request的body内容（json或bytes）
	- 检查函数级别的stack（fastapi_inner_astack）是否存在并获取
	- 调用`solve_dependencies`方法解析依赖并获取solved_results
	- 解析依赖未报错，则进行下一步；否则直接`raise RequestValidationError`
	- 判断是否为sse_stream类型进行处理
	- 判断是否为json_stream类型进行处理
	- 判断dependant.call是否异步可调用或可调用，调用并进行处理
	- 如果以上判断都不符合，则通过`run_endpoint_function`方法直接运行dependant.call的endpoint方法并获取Response封装序列化
	- 最后`assert response`并返回
```python
if not errors:
	# Shared serializer for stream items (JSONL and SSE).
	# Validates against stream_item_field when set, then
	# serializes to JSON bytes.
	def _serialize_data(data: Any) -> bytes:
		...

	if is_sse_stream:
		# Generator endpoint: stream as Server-Sent Events
		gen = dependant.call(**solved_result.values)

		...

		response = StreamingResponse(
			sse_stream_content,
			media_type="text/event-stream",
			**response_args,
		)
		...
	elif is_json_stream:
		# Generator endpoint: stream as JSONL
		gen = dependant.call(**solved_result.values)

		...

		response = StreamingResponse(
			jsonl_stream_content,
			media_type="application/jsonl",
			**response_args,
		)
		....
	elif _is_async_gen_callable(dependant.call) or _is_gen_callable(
		dependant.call
	):
		# Raw streaming with explicit response_class (e.g. StreamingResponse)
		gen = dependant.call(**solved_result.values)

		...

		response = actual_response_class(content=gen, **response_args)
		
	else:
		raw_response = await run_endpoint_function(
			dependant=dependant,
			values=solved_result.values,
			is_coroutine=is_coroutine,
		)
		if isinstance(raw_response, Response):
			...
			response = raw_response
		else:
			...
			
			if use_dump_json:
				response = Response(
					content=content,
					media_type="application/json",
					**response_args,
				)
			else:
				response = actual_response_class(content, **response_args)
			if not is_body_allowed_for_status_code(response.status_code):
				response.body = b""
			...
if errors:
	validation_error = RequestValidationError(
		errors, body=body, endpoint_ctx=endpoint_ctx
	)
	raise validation_error

# Return response
assert response
return response
```

## 依赖注入（solve_dependencies方法）

