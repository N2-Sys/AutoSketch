## 总体使用
进入到文件夹下输入以下下命令
```
mkdir build
mkdir out
cd build
cmake ..
make
```
在out文件加下就会出现`preprocess`文件用于`.pcap`文件的预处理

## 数据集的处理

对网络数据抓包后得到的文件是`.pcap`文件，它包含原始数据包的所有信息。但是我们实验时一般只关注部分信息，例如ip地址、时间戳、报文大小等。每次都读取`.pcap`文件比较繁琐，所以我们会先对它处理，提取有用信息并生成一个二进制`.bin`文件。之后我们只需要读`.bin`文件就可以了。

### 如何处理.pcap文件

`pcap_preprocess.c`文件是用来实现以上功能的。CMakeLists.txt中可看出，它会生成`preprocess`可执行文件。
使用方法：
`./preprocess input_dir input_file output_file`

- `input_dir`: `.pcap`文件所在目录。
- `input_file`: `.pcap`文件的文件名。
- `output_file`: 预处理后的输出文件名。

举例：`./preprocess /home/zjq/data/  equinix-nyc.dirA.20180315-130000.UTC.anon.pcap  flow.bin`。注意文件`input_dir`最后要加`/`

然后就会在`input_dir`目录下生成`output_file`了。
