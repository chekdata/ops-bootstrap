/speckit.constitution /Users/jasonhong/Desktop/CICD/ops-bootstrap/.specify/memory/constitution.md

——

/speckit.specify /Users/jasonhong/Desktop/CICD/ops-bootstrap/.specify/memory/specify.md

——

/Users/jasonhong/Desktop/CICD/ops-bootstrap/研发使用指南.md
根据上面文档。

帮我把 https://github.com/chekdata/backend-saas.git这个切出Dev、staging分支，分别部署到Dev、staging、prod（main）三个环境里。

看需要我给你提供什么？密钥都在/Users/jasonhong/Desktop/CICD/ops-bootstrap/_local/.env.local
当前环境的节点+性能够用吗？如果不够，你自己开。

——

全文查看/Users/jasonhong/Desktop/CICD/ops-bootstrap/研发使用指南.md，
/Users/jasonhong/Desktop/CICD/ops-bootstrap/服务运维手册.md


https://github.com/chekdata/backend-gateway-saas.git

这个项目的CICD还有什么待办项目吗？
github一合并，CD就能自动地完整走完了吗？


——
【后端服务部署】
你验证osm-gateway这个项目的CICD在三个环境的整个流程了吗？github一合并，CD就能自动地完整走完了吗？ALB的规则准确吗？验证了项目在api.chekkk.com联通性了吗？项目的各种接口能用了吗？项目在nacos生效了吗会自动同步么？项目在yapi有了吗？yapi会自动同步么？yapi里工作流llm帮忙丰富了哪些东西？

——
【前端服务部署】
现在Github的PR一合并，CICD就能自动地完整走完三个环境的部署了吗？yapi会自动同步么？飞书拉群和飞书通知自动会有吗？不希望挨个去调用工作流，它应该是PR一合并就自动触发的
——

github云端各种没有用的工作流帮我清掉，日常在使用的保留好。
github云端在部署过程中用到的各种分支帮我判断是否有用，都整理一下，没有用的关闭掉（仅限在部署过程中用到的各种分支）
github云端在部署过程中用到的各种PR帮我判断，没有用的关闭掉。
火山引擎镜像仓库里的临时镜像或者旧的没有用的镜像也帮我清理掉
github代码仓库里跟部署相关的临时文件或者旧的没有用的文件也帮我清理掉

不要用粗暴脚本方式来清理，而且抓取现有的所有情况。你（LLM）针对每一个做一个处理判断，然后再执行处理。不容易出错。

——

这次部署相关的洞察帮我更新进/Users/jasonhong/Desktop/CICD/ops-bootstrap/研发使用指南.md。
还有更新/Users/jasonhong/Desktop/CICD/ops-bootstrap/服务运维手册.md，便于以后运维

——

action错误工作流纠正prompt：
用 gh run view --log 把最近主要失败的 run 都拉到本地