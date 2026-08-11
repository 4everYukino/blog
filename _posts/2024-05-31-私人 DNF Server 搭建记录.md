---
layout: post
title: 私人 DNF Server 的基本概念、搭建过程、问题记录
author: Bruce
tag: 技术
---

由于 DNF 台服流出了 70 版本的 Server，故现在几乎所有私服均以其作为底板，并在此基础上通过修改 dp(dnf plugin) 插件和修改 Script.pvf 文件的方式来进行修改。

本文只用于学习、交流，作者搭建 Server 也仅仅是为了自己怀旧一下，所有知识、资源均来自于百度贴吧：台服DNF吧。

感谢所有人的付出。

最后，请不要窃取别人的劳动成果来谋取私利，更况且只是蝇头小利。

---

## 架构介绍

其实非常直观，三大组件：Server、数据库、Client。

### Server

主要是用于接收并处理 Client 的请求，这里使用贴吧的一键部署即可。

若要修改 Server 主要就是修改以下三个关键的文件：

* 一个可执行文件 `df_game_r` 决定了等级的上限
* `publickey.pem`
* 游戏版本文件 `Script.pvf` 决定了一些物品(item)、地图。

### 数据库

就是一个 MySQL Server，存储了所有角色信息。

其中各个库，各张表所存储的逻辑，部分 GM 工具已经总结得很好了（因为它们需要用到），有需要的话建议参考：

> https://gitee.com/AsakuraYou/dnf__-gm_-tools/blob/master/DOF%20GM%20Tool%E8%AF%B4%E6%98%8E.png

贴吧的一键部署就会将其部署好。

### Client

现在广泛使用的客户端(dnf.exe)分为 0627 和 1031 版本，具体如何区分我暂时还不知道。

大致就是先经过登录器，填入 Server IP 和你的账号密码等信息，向 Server 发起验证，通过后即自动调用 DNF.exe 来进行游戏。

另外，客户端也已经广泛包含了一系列补丁合集，也就是我们以前会用到的外挂，主要用于处理本地的逻辑，比如：固定 SSS 评分、顺图、一键分解等功能，用以代替人为操作。

___
## 一般流程

一般情况下，使用一键部署端部署好之后，替换如下三个文件：
* `df_game_r`
* `publickey.pem`
* `Script.pvf`

然后执行 `/root/run`，当看到跑出 "五国" 且没有其他报错即可认为成功。

```
[13:33:41] GeoIP Allow Country Code : CN
[13:33:41] GeoIP Allow Country Code : HK
[13:33:41] GeoIP Allow Country Code : KR
[13:33:41] GeoIP Allow Country Code : MO
[13:33:41] GeoIP Allow Country Code : TW
[13:33:41] [!] Guild Server Connected
[13:33:51] [!] Connect To Monitor Server ...
[13:33:51] [!] Connect To Guild Server ...
```

> P.S.
> 这里所谓 "五国" 只是遵从贴吧说法，实际上台湾(TW)属于中国的一部分。

另外，由于无法直接修改 Server，有一些作者修改通过 dp 插件来达到一些效果，实际上就是写了一个动态库，动态载入并调用对应函数来做到一些效果。

比如 `神迹·因果` 版本在商场里就有一些一键完成任务的道具，就是类似效果来实现的。

这种情况下，需要执行 `/root/dprun` 而不是 `/root/run`，判断是否成功跟上述一致，另外，日志文件夹中 (`/home/neople/game/log`) 会多出一个 dp 的日志，可以自行检查有无错误。

---

## 问题记录

### 为什么出现 Fail to init channel 之类的报错？

笔者检查 `/var/log/messages` 发现是一个进程 `df_bridge` 被 OOM kill 掉了，增大内存 or 尝试重启解决。

### 为什么一连接频道就网络连接中断？

这种情况一般是公钥对不上，自行检查。
