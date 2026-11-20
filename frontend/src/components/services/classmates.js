function nameParts(row) {
  const words = (row.student_name ?? '').trim().split(/\s+/);
  return [words.pop(), words.join(' ')];
}

export function compareClassmates(a, b) {
  const [nameA, familyA] = nameParts(a);
  const [nameB, familyB] = nameParts(b);
  return nameA.localeCompare(nameB, 'vi') || familyA.localeCompare(familyB, 'vi');
}
