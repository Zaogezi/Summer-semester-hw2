问题：最初judge目录在app内，会引发uvicorn重载打断测评
解决：目录放在app外

问题：pytest无权创建或修改目录
解决：在pytest中使用内存SQList，不创建临时数据库（迁移到wsl？）