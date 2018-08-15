<pre>
###################################################################
#                           MyFTP                                 #
#                      author: Dev-L                              #
#                     Date: 2018/8/14                             #
###################################################################
</pre>
8/14/2018 5:36:33 PM 
## MyFTP V1.0.0 Intro
- 用户注册、登录、分配磁盘空间
- 多日志记录客户端连接、用户注册、登录信息
- 支持多用户同时登录（内部实现为基于Queue定制的ThreadPool）
- 支持自定义最大并发数
- 支持用户查看账号下的目录及文件
- 支持切换目录、创建目录、删除目录及文件
- 支持用户批量上传、下载文件
- 支持断点续传和文件一致性校验

## Usage
### Sever端
- 启动：

    `cd MyFtpServer/bin `

    `python run.py runserver`

	也可指定ip和端口：`python run.py runserver --ip 0.0.0.0 -p 8000`

- 关闭

	`CTRL+C` 

	主线程监听了中断信号，同时按下CTRL和C即可终止Sever端



### Client端
- 启动：

    `cd MyFtpClient/bin `

    登录： `python run.py -s server_ip -P port - u username -p password login`
	
	注册： `python run.py -s server_ip -P port signup`
	
	输入 -h/--help 显示帮助

- 使用MyFTP

	登录成功后，即可正常使用MyFTP, 命令列表如下：
	
	- `ls` &emsp; &emsp; 展示当前目录下的文件及子目录
	- `cd dirname` &emsp; &emsp; 切换目录
	- `mkdir dirname` &emsp; &emsp; 在当前目录下创建新目录（支持递归创建）
	- `remove file_or_dir_name` &emsp; &emsp; 移除目标文件或目录(直接移除！)
	- `put file1 file2 file3 ...` &emsp; &emsp; 批量上传多个文件，以空格分隔
	- `get file1 file2 file3 ...` &emsp; &emsp; 批量下载多个文件，以空格分割
	
### TODO
- `ls target_dir` &emsp; &emsp; 展示目标目录下的文件及子目录
- `get dir_name` &emsp; &emsp; 递归下载指定目录下的所有文件
- `put dir_name` &emsp; &emsp; 递归上传指定目录下的所有文件

## Directory structure
### MyFtpSever

<pre>
MyFtpServer
├── bin
│   ├── __init__.py
│   └── run.py
├── conf
│   ├── __init__.py
│   └── settings.py
├── core
│   ├── __init__.py
│   ├── logger.py
│   ├── server.py
│   └── threadpool.py
├── db
│   ├── __init__.py
│   ├── lee
│   ├── sam
│   └── user_info.dat
├── __init__.py
└── log
    ├── conn.log
    ├── __init__.py
    ├── login.log
    └── signup.log
</pre>

### MyFtpClient

<pre>
MyFtpClient                       
├── bin                 
│   ├── book.pdf        
│   ├── __init__.py     
│   ├── run.py          
│   └── test.pdf        
├── conf                
│   ├── __init__.py     
│   └── settings.py     
├── core                
│   ├── client.py       
│   └── __init__.py     
├── download            
│   └── client.py       
├── __init__.py         
└── log                 
    └── __init__.py  
</pre>

