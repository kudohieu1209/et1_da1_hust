// Thu nhỏ ảnh đại diện trước khi lưu: ảnh gốc vài MB nằm trong hồ sơ sẽ bị gửi
// kèm mọi phản hồi /api/student/audit. 256px JPEG thường chỉ ~20-40KB.

export const AVATAR_SIZE_PX = 256;
export const ACCEPTED_AVATAR_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
const MAX_SOURCE_BYTES = 10 * 1024 * 1024;
const JPEG_QUALITY = 0.85;

function loadImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('unreadable'));
    };
    image.src = url;
  });
}

/**
 * Cắt vuông ở giữa và thu về AVATAR_SIZE_PX, trả về data URL JPEG.
 * @param {File} file
 * @returns {Promise<string>}
 */
export async function resizeAvatar(file) {
  if (!ACCEPTED_AVATAR_TYPES.includes(file.type)) throw new Error('type');
  if (file.size > MAX_SOURCE_BYTES) throw new Error('size');

  const image = await loadImage(file);
  const side = Math.min(image.naturalWidth, image.naturalHeight);
  const canvas = document.createElement('canvas');
  canvas.width = AVATAR_SIZE_PX;
  canvas.height = AVATAR_SIZE_PX;
  const context = canvas.getContext('2d');
  context.drawImage(
    image,
    (image.naturalWidth - side) / 2,
    (image.naturalHeight - side) / 2,
    side,
    side,
    0,
    0,
    AVATAR_SIZE_PX,
    AVATAR_SIZE_PX,
  );
  return canvas.toDataURL('image/jpeg', JPEG_QUALITY);
}
