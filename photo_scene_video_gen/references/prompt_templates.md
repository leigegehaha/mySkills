# Prompt Templates

## 1. 通用图片提示词模板

```text
Use the provided face as the identity reference. Create a realistic [aspect ratio] scene in [scene].
The same woman/man appears in the scene, wearing [outfit], doing [action].
Keep strong identity consistency with the reference face, photorealistic, high detail, natural body proportions,
clean composition, realistic lighting, no subtitles, no text.
```

## 2. 自拍图片提示词模板

```text
这是一张iPhone前置摄像头拍摄的自拍照片儿。
Use the provided face as the identity reference. Create a realistic [aspect ratio] scene in [scene]
from a true iPhone front-camera selfie perspective. The same person is personally holding the phone.
The composition must clearly lock to a handheld front-camera selfie: close arm-length framing,
slight wide-angle lens feel, and part of the hand / wrist / forearm subtly visible near the frame edge.
This must not look like a third-person shot. The person is wearing [outfit], doing [action].
Photorealistic, high detail, strong identity consistency, no subtitles, no text.
```

## 3. 自拍视频提示词模板

```text
Vertical [aspect ratio] iPhone front-camera selfie video in [scene].
The same person keeps the same face and appearance as the reference image and is holding the phone
personally for the entire clip. Keep true selfie perspective from start to end, never switch to
third-person view, and keep part of the hand, wrist, or forearm subtly visible near the edge of frame
throughout so the phone-held selfie angle stays consistent.
Close arm-length framing, slight iPhone wide-angle look, gentle handheld selfie shake.
The person does [action] and says: '[dialogue]'.
Natural lip movement, no subtitles, maintain identity consistency.
```

## 4. 后置固定机位模板

```text
Use the provided face as the identity reference. Create a realistic [aspect ratio] scene in [scene],
filmed by a fixed smartphone rear camera on a tripod or stand, not a selfie frame.
The same person is wearing [outfit], doing [action]. Keep strong identity consistency, photorealistic,
natural environment detail, no subtitles, no text.
```

## 5. 后置固定机位视频模板

```text
Vertical [aspect ratio] fixed smartphone rear-camera video in [scene].
The same person keeps the same face and appearance as the reference image.
The camera is fixed on a stand or tripod, not a selfie perspective.
The person does [action] and says: '[dialogue]'.
Natural lip movement, no subtitles, maintain identity consistency.
```
