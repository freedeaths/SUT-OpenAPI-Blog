# SUT(System Under Test) - 基于 Swagger2.0 的博客后端

因为它的目的是为了设计一个自动生成和执行端到端场景测试用例的工具，它需要通过跟 SUT 的交互来实现自动化测试，因此需要一个 SUT，满足我的一些实验需求。

## 主要要求

- 基于 Swagger2.0 实现博客后端
- 基于 FastAPI 实现博客后端
- 用 Sqlite3 作为数据库
- 必须写 pytest 测试用例，用 TDD 来指导开发

## 领域模型设计

### 实体设计

```
User
- id: UUID
- username: str
- email: str
- password_hash: str
- bio: str
- created_at: datetime
- last_login: datetime
- is_active: bool

Post
- id: UUID
- author_id: UUID (FK -> User)
- title: str
- content: str
- status: PostStatus (DRAFT/ACTIVE/ARCHIVED)
- created_at: datetime
- updated_at: datetime
- likes_count: int
- dislikes_count: int
- views_count: int
- comments_count: int

Comment
- id: UUID
- post_id: UUID (FK -> Post)
- author_id: UUID (FK -> User)
- content: str
- status: CommentStatus (ACTIVE/HIDDEN/DELETED)
- created_at: datetime
- updated_at: datetime
- likes_count: int
- dislikes_count: int
- replies_count: int

Reply
- id: UUID
- comment_id: UUID (FK -> Comment)
- author_id: UUID (FK -> User)
- content: str
- status: ReplyStatus (ACTIVE/HIDDEN/DELETED)
- created_at: datetime
- updated_at: datetime
- likes_count: int
- dislikes_count: int

Reaction
- id: UUID
- user_id: UUID (FK -> User)
- target_type: str (POST/COMMENT/REPLY)
- target_id: UUID
- type: ReactionType (LIKE/DISLIKE)
- created_at: datetime

Tag
- id: UUID
- name: str (unique)
- description: str
- created_at: datetime
- updated_at: datetime
- posts_count: int

PostTag
- post_id: UUID (FK -> Post)
- tag_id: UUID (FK -> Tag)
- created_at: datetime
```

### 业务规则

#### Post 规则
- DRAFT 状态只有作者可见
- ACTIVE 状态所有人可见且可评论
- ARCHIVED 状态所有人可见但不可评论
- 只有作者可以更改状态
- 用户可以对一个 Post 点赞或点踩，但不能同时进行
- Post 被 archived 时，其下所有 comment 状态改为 HIDDEN
- Post 可以被作者删除，删除时会级联删除其下所有 comments 和 replies
- Post 有 MODIFYING 状态，此状态下：
  - 不允许创建新的评论
  - 现有评论仍然可见
  - 只有作者可以修改内容
  - 可以从 ACTIVE 切换到 MODIFYING，再切回 ACTIVE
  - 不能从 ARCHIVED 切换到 MODIFYING

#### Comment 规则
- 只能在 ACTIVE 状态的 Post 下创建
- 作者可以删除自己的评论
- Post 作者可以隐藏任何评论
- Comment 被删除时，其下所有 reply 状态改为 DELETED
- 用户可以对一个 Comment 点赞或点踩，但不能同时进行
- Comment 被删除时会级联删除其下所有 replies
- Comment 有 MODIFYING 状态，此状态下：
  - 不允许创建新的回复
  - 现有回复仍然可见
  - 只有作者可以修改内容
  - 可以从 ACTIVE 切换到 MODIFYING，再切回 ACTIVE
  - 不能从 DELETED 或 HIDDEN 状态切换到 MODIFYING

#### Reply 规则
- 只能回复 ACTIVE 状态的 Comment
- 作者可以删除自己的回复
- Comment 作者和 Post 作者可以隐藏任何回复
- 用户可以对一个 Reply 点赞或点踩，但不能同时进行

#### Tag 规则
- Tag name 必须唯一
- 只有当 posts_count 为 0 时才能删除 Tag
- 更新 Tag 时只能修改 description
- 添加/删除文章标签时自动更新 posts_count
- Tag name 不能包含特殊字符，只允许字母、数字、中文和连字符
- 创建 Tag 时自动将 name 转为小写

## 测试用例设计

### User 相关测试

1. POST /users
   - 使用有效数据创建用户成功
   - 使用重复的用户名创建用户失败
   - 使用无效的邮箱格式创建用户失败
   - 密码不符合复杂度要求时创建失败

2. GET /users/{userId}
   - 获取存在的用户信息成功
   - 获取不存在的用户返回404
   - 获取已删除的用户返回404
   - 验证返回的用户信息字段完整性

### Post 相关测试

1. POST /posts
   - 成功创建草稿状态的文章
   - 成功创建并直接发布文章
   - 标题超过长度限制时创建失败
   - 未授权用户创建文章失败

2. PUT /posts/{postId}/status
   - 作者将草稿改为发布状态成功
   - 作者将发布文章改为归档状态成功
   - 非作者修改状态失败
   - 从归档状态改为发布状态失败

3. DELETE /posts/{postId}
   - 作者删除文章成功，验证关联评论和回复被删除
   - 非作者删除文章失败
   - 删除带有评论的文章，验证级联删除成功
   - 删除已删除的文章返回404

4. PUT /posts/{postId}/status (MODIFYING 相关)
   - 作者将 ACTIVE 文章切换为 MODIFYING 状态成功
   - MODIFYING 状态下创建评论失败
   - 非作者修改 MODIFYING 状态文章内容失败
   - 从 ARCHIVED 切换到 MODIFYING 失败
   - MODIFYING 状态成功切换回 ACTIVE

### Comments 相关测试

1. POST /posts/{postId}/comments
   - 在活动文章下成功创建评论
   - 在归档文章下创建评论失败
   - 创建空内容评论失败
   - 未登录用户创建评论失败

2. PUT /posts/{postId}/comments/{commentId}/status
   - 评论作者隐藏自己的评论成功
   - 文章作者隐藏他人评论成功
   - 非相关用户修改评论状态失败
   - 修改已删除评论状态失败

3. DELETE /posts/{postId}/comments/{commentId}
   - 作者删除评论成功，验证关联回复被删除
   - 文章作者删除他人评论成功
   - 非相关用户删除评论失败
   - 删除已删除的评论返回404

4. PUT /posts/{postId}/comments/{commentId}/status (MODIFYING 相关)
   - 作者将 ACTIVE 评论切换为 MODIFYING 状态成功
   - MODIFYING 状态下创建回复失败
   - 非作者修改 MODIFYING 状态评论内容失败
   - 从 HIDDEN 切换到 MODIFYING 失败
   - MODIFYING 状态成功切换回 ACTIVE

### Reply 相关测试

1. POST /posts/{postId}/comments/{commentId}/replies
   - 对活动评论创建回复成功
   - 对隐藏评论创建回复失败
   - 创建空内容回复失败
   - 未登录用户创建回复失败

2. DELETE /posts/{postId}/comments/{commentId}/replies/{replyId}
   - 作者删除自己的回复成功
   - 评论作者删除他人回复成功
   - 非相关用户删除回复失败
   - 删除已删除的回复返回404

### Tag 相关测试

1. POST /tags
   - 创建有效标签成功
   - 创建重复名称标签失败
   - 创建包含特殊字符的标签失败
   - 验证标签名自动转为小写

2. DELETE /tags/{tagId}
   - 删除无关联文章的标签成功
   - 删除有关联文章的标签失败
   - 删除不存在的标签返回404
   - 普通用户删除标签失败

### Reaction 相关测试

1. POST /reactions
   - 用户成功对文章点赞
   - 重复点赞失败
   - 将点赞改为点踩成功
   - 对不存在的目标创建反应失败

2. DELETE /reactions
   - 成功删除已有反应
   - 删除不存在的反应返回404
   - 删除他人的反应失败
   - 验证计数器正确减少

### 状态流转测试

1. Post 状态流转
  - DRAFT -> ACTIVE -> MODIFYING -> ACTIVE -> ARCHIVED
  - DRAFT -> ACTIVE -> ARCHIVED (不能切换到 MODIFYING)

2. Comment 状态流转
  - ACTIVE -> MODIFYING -> ACTIVE
  - ACTIVE -> HIDDEN (不能切换到 MODIFYING)
  - ACTIVE -> DELETED (不能切换到 MODIFYING)