/**
 * Sample Test Data Fixtures
 * Realistic sample data untuk testing export system
 */

/**
 * Sample hierarchy rows
 * Struktur: Klasifikasi → Sub-klasifikasi → Pekerjaan (3 levels)
 */
export const sampleHierarchyRows = [
  // Klasifikasi 1: Pekerjaan Persiapan
  {
    id: 1,
    type: 'klasifikasi',
    level: 0,
    parentId: null,
    name: 'Pekerjaan Persiapan'
  },
  {
    id: 2,
    type: 'pekerjaan',
    level: 1,
    parentId: 1,
    name: 'Mobilisasi Alat Berat'
  },
  {
    id: 3,
    type: 'pekerjaan',
    level: 1,
    parentId: 1,
    name: 'Pembersihan Lahan'
  },
  {
    id: 4,
    type: 'pekerjaan',
    level: 1,
    parentId: 1,
    name: 'Pengukuran dan Pematokan'
  },

  // Klasifikasi 2: Pekerjaan Tanah
  {
    id: 5,
    type: 'klasifikasi',
    level: 0,
    parentId: null,
    name: 'Pekerjaan Tanah'
  },
  {
    id: 6,
    type: 'sub-klasifikasi',
    level: 1,
    parentId: 5,
    name: 'Galian Tanah'
  },
  {
    id: 7,
    type: 'pekerjaan',
    level: 2,
    parentId: 6,
    name: 'Galian Tanah Biasa'
  },
  {
    id: 8,
    type: 'pekerjaan',
    level: 2,
    parentId: 6,
    name: 'Galian Tanah Keras'
  },
  {
    id: 9,
    type: 'sub-klasifikasi',
    level: 1,
    parentId: 5,
    name: 'Urugan Tanah'
  },
  {
    id: 10,
    type: 'pekerjaan',
    level: 2,
    parentId: 9,
    name: 'Urugan Tanah Kembali'
  },
  {
    id: 11,
    type: 'pekerjaan',
    level: 2,
    parentId: 9,
    name: 'Pemadatan Tanah'
  },

  // Klasifikasi 3: Pekerjaan Pondasi
  {
    id: 12,
    type: 'klasifikasi',
    level: 0,
    parentId: null,
    name: 'Pekerjaan Pondasi'
  },
  {
    id: 13,
    type: 'pekerjaan',
    level: 1,
    parentId: 12,
    name: 'Pondasi Batu Kali'
  },
  {
    id: 14,
    type: 'pekerjaan',
    level: 1,
    parentId: 12,
    name: 'Pondasi Footplate'
  },
  {
    id: 15,
    type: 'pekerjaan',
    level: 1,
    parentId: 12,
    name: 'Sloof Beton Bertulang'
  },

  // Klasifikasi 4: Pekerjaan Struktur
  {
    id: 16,
    type: 'klasifikasi',
    level: 0,
    parentId: null,
    name: 'Pekerjaan Struktur'
  },
  {
    id: 17,
    type: 'sub-klasifikasi',
    level: 1,
    parentId: 16,
    name: 'Kolom'
  },
  {
    id: 18,
    type: 'pekerjaan',
    level: 2,
    parentId: 17,
    name: 'Kolom Lantai 1'
  },
  {
    id: 19,
    type: 'pekerjaan',
    level: 2,
    parentId: 17,
    name: 'Kolom Lantai 2'
  },
  {
    id: 20,
    type: 'sub-klasifikasi',
    level: 1,
    parentId: 16,
    name: 'Balok'
  },
  {
    id: 21,
    type: 'pekerjaan',
    level: 2,
    parentId: 20,
    name: 'Balok Lantai 1'
  },
  {
    id: 22,
    type: 'pekerjaan',
    level: 2,
    parentId: 20,
    name: 'Balok Lantai 2'
  },
  {
    id: 23,
    type: 'sub-klasifikasi',
    level: 1,
    parentId: 16,
    name: 'Plat Lantai'
  },
  {
    id: 24,
    type: 'pekerjaan',
    level: 2,
    parentId: 23,
    name: 'Plat Lantai 1'
  },
  {
    id: 25,
    type: 'pekerjaan',
    level: 2,
    parentId: 23,
    name: 'Plat Lantai 2'
  },

  // Klasifikasi 5: Pekerjaan Finishing
  {
    id: 26,
    type: 'klasifikasi',
    level: 0,
    parentId: null,
    name: 'Pekerjaan Finishing'
  },
  {
    id: 27,
    type: 'pekerjaan',
    level: 1,
    parentId: 26,
    name: 'Plesteran Dinding'
  },
  {
    id: 28,
    type: 'pekerjaan',
    level: 1,
    parentId: 26,
    name: 'Pengecatan'
  },
  {
    id: 29,
    type: 'pekerjaan',
    level: 1,
    parentId: 26,
    name: 'Pemasangan Keramik'
  },
  {
    id: 30,
    type: 'pekerjaan',
    level: 1,
    parentId: 26,
    name: 'Pemasangan Plafon'
  }
];

/**
 * Sample week columns (26 weeks = 6.5 months)
 */
export const sampleWeekColumns = [
  { week: 1, startDate: '2025-01-06T00:00:00Z', endDate: '2025-01-12T23:59:59Z' },
  { week: 2, startDate: '2025-01-13T00:00:00Z', endDate: '2025-01-19T23:59:59Z' },
  { week: 3, startDate: '2025-01-20T00:00:00Z', endDate: '2025-01-26T23:59:59Z' },
  { week: 4, startDate: '2025-01-27T00:00:00Z', endDate: '2025-02-02T23:59:59Z' },
  { week: 5, startDate: '2025-02-03T00:00:00Z', endDate: '2025-02-09T23:59:59Z' },
  { week: 6, startDate: '2025-02-10T00:00:00Z', endDate: '2025-02-16T23:59:59Z' },
  { week: 7, startDate: '2025-02-17T00:00:00Z', endDate: '2025-02-23T23:59:59Z' },
  { week: 8, startDate: '2025-02-24T00:00:00Z', endDate: '2025-03-02T23:59:59Z' },
  { week: 9, startDate: '2025-03-03T00:00:00Z', endDate: '2025-03-09T23:59:59Z' },
  { week: 10, startDate: '2025-03-10T00:00:00Z', endDate: '2025-03-16T23:59:59Z' },
  { week: 11, startDate: '2025-03-17T00:00:00Z', endDate: '2025-03-23T23:59:59Z' },
  { week: 12, startDate: '2025-03-24T00:00:00Z', endDate: '2025-03-30T23:59:59Z' },
  { week: 13, startDate: '2025-03-31T00:00:00Z', endDate: '2025-04-06T23:59:59Z' },
  { week: 14, startDate: '2025-04-07T00:00:00Z', endDate: '2025-04-13T23:59:59Z' },
  { week: 15, startDate: '2025-04-14T00:00:00Z', endDate: '2025-04-20T23:59:59Z' },
  { week: 16, startDate: '2025-04-21T00:00:00Z', endDate: '2025-04-27T23:59:59Z' },
  { week: 17, startDate: '2025-04-28T00:00:00Z', endDate: '2025-05-04T23:59:59Z' },
  { week: 18, startDate: '2025-05-05T00:00:00Z', endDate: '2025-05-11T23:59:59Z' },
  { week: 19, startDate: '2025-05-12T00:00:00Z', endDate: '2025-05-18T23:59:59Z' },
  { week: 20, startDate: '2025-05-19T00:00:00Z', endDate: '2025-05-25T23:59:59Z' },
  { week: 21, startDate: '2025-05-26T00:00:00Z', endDate: '2025-06-01T23:59:59Z' },
  { week: 22, startDate: '2025-06-02T00:00:00Z', endDate: '2025-06-08T23:59:59Z' },
  { week: 23, startDate: '2025-06-09T00:00:00Z', endDate: '2025-06-15T23:59:59Z' },
  { week: 24, startDate: '2025-06-16T00:00:00Z', endDate: '2025-06-22T23:59:59Z' },
  { week: 25, startDate: '2025-06-23T00:00:00Z', endDate: '2025-06-29T23:59:59Z' },
  { week: 26, startDate: '2025-06-30T00:00:00Z', endDate: '2025-07-06T23:59:59Z' }
];

/**
 * Sample planned progress
 * Structure: pekerjaan_id -> { week -> progress }
 * Progress mengikuti kurva S (slow start, fast middle, slow end)
 */
export const samplePlannedProgress = {
  // Pekerjaan Persiapan (W1-W4)
  2: { 1: 25, 2: 60, 3: 85, 4: 100 }, // Mobilisasi
  3: { 1: 20, 2: 50, 3: 80, 4: 100 }, // Pembersihan
  4: { 2: 30, 3: 70, 4: 100 },        // Pengukuran

  // Pekerjaan Tanah (W3-W8)
  7: { 3: 10, 4: 25, 5: 50, 6: 75, 7: 90, 8: 100 }, // Galian Biasa
  8: { 4: 15, 5: 35, 6: 60, 7: 85, 8: 100 },        // Galian Keras
  10: { 6: 20, 7: 50, 8: 80, 9: 100 },              // Urugan
  11: { 7: 25, 8: 60, 9: 90, 10: 100 },             // Pemadatan

  // Pekerjaan Pondasi (W8-W12)
  13: { 8: 15, 9: 35, 10: 60, 11: 85, 12: 100 },    // Batu Kali
  14: { 9: 20, 10: 45, 11: 75, 12: 100 },           // Footplate
  15: { 10: 25, 11: 60, 12: 90, 13: 100 },          // Sloof

  // Pekerjaan Struktur Lantai 1 (W12-W18)
  18: { 12: 10, 13: 25, 14: 50, 15: 75, 16: 90, 17: 100 }, // Kolom L1
  21: { 14: 15, 15: 35, 16: 60, 17: 85, 18: 100 },         // Balok L1
  24: { 16: 20, 17: 50, 18: 80, 19: 100 },                 // Plat L1

  // Pekerjaan Struktur Lantai 2 (W18-W24)
  19: { 18: 10, 19: 25, 20: 50, 21: 75, 22: 90, 23: 100 }, // Kolom L2
  22: { 20: 15, 21: 35, 22: 60, 23: 85, 24: 100 },         // Balok L2
  25: { 22: 20, 23: 50, 24: 80, 25: 100 },                 // Plat L2

  // Pekerjaan Finishing (W23-W26)
  27: { 23: 15, 24: 40, 25: 70, 26: 100 }, // Plesteran
  28: { 24: 20, 25: 55, 26: 90 },          // Pengecatan (ongoing)
  29: { 24: 25, 25: 60, 26: 95 },          // Keramik (ongoing)
  30: { 25: 30, 26: 70 }                   // Plafon (ongoing)
};

/**
 * Sample actual progress (with delays and gaps)
 * Actual biasanya sedikit lebih lambat dari planned
 */
export const sampleActualProgress = {
  // Pekerjaan Persiapan (delayed 1 week)
  2: { 1: 20, 2: 50, 3: 75, 4: 95, 5: 100 },
  3: { 1: 15, 2: 40, 3: 70, 4: 95, 5: 100 },
  4: { 2: 25, 3: 60, 4: 90, 5: 100 },

  // Pekerjaan Tanah (slight delay + gap at W5)
  7: { 3: 8, 4: 20, 6: 45, 7: 70, 8: 90, 9: 100 }, // Gap di W5
  8: { 4: 12, 5: 30, 6: 55, 7: 80, 8: 95, 9: 100 },
  10: { 6: 18, 7: 45, 8: 75, 9: 95, 10: 100 },
  11: { 7: 20, 8: 55, 9: 85, 10: 98, 11: 100 },

  // Pekerjaan Pondasi (on track)
  13: { 8: 15, 9: 35, 10: 60, 11: 85, 12: 100 },
  14: { 9: 18, 10: 42, 11: 72, 12: 98, 13: 100 },
  15: { 10: 22, 11: 58, 12: 88, 13: 100 },

  // Pekerjaan Struktur Lantai 1 (delayed)
  18: { 12: 8, 13: 20, 14: 45, 15: 70, 16: 85, 17: 95, 18: 100 },
  21: { 14: 12, 15: 30, 16: 55, 17: 80, 18: 95, 19: 100 },
  24: { 16: 18, 17: 45, 18: 75, 19: 95, 20: 100 },

  // Pekerjaan Struktur Lantai 2 (ongoing)
  19: { 18: 8, 19: 22, 20: 48, 21: 72, 22: 88, 23: 98 },
  22: { 20: 12, 21: 32, 22: 58, 23: 82, 24: 96 },
  25: { 22: 18, 23: 48, 24: 78, 25: 96 },

  // Pekerjaan Finishing (just started)
  27: { 23: 12, 24: 35, 25: 65, 26: 92 },
  28: { 24: 18, 25: 50, 26: 85 },
  29: { 24: 22, 25: 55, 26: 88 },
  30: { 25: 28, 26: 65 }
};

/**
 * Sample Kurva S data (cumulative weekly)
 * Calculated from all pekerjaan progress
 */
export const sampleKurvaSData = [
  { week: 1, planned: 3.5, actual: 2.8 },
  { week: 2, planned: 7.2, actual: 5.9 },
  { week: 3, planned: 11.8, actual: 9.5 },
  { week: 4, planned: 16.5, actual: 13.2 },
  { week: 5, planned: 20.3, actual: 16.8 },
  { week: 6, planned: 24.8, actual: 20.5 },
  { week: 7, planned: 29.5, actual: 24.8 },
  { week: 8, planned: 34.2, actual: 29.2 },
  { week: 9, planned: 38.8, actual: 33.5 },
  { week: 10, planned: 43.5, actual: 38.2 },
  { week: 11, planned: 48.2, actual: 42.8 },
  { week: 12, planned: 52.8, actual: 47.5 },
  { week: 13, planned: 56.5, actual: 51.2 },
  { week: 14, planned: 60.2, actual: 54.8 },
  { week: 15, planned: 63.8, actual: 58.5 },
  { week: 16, planned: 67.5, actual: 62.2 },
  { week: 17, planned: 71.2, actual: 66.8 },
  { week: 18, planned: 74.8, actual: 70.5 },
  { week: 19, planned: 77.5, actual: 73.8 },
  { week: 20, planned: 80.2, actual: 77.2 },
  { week: 21, planned: 82.8, actual: 80.5 },
  { week: 22, planned: 85.5, actual: 83.8 },
  { week: 23, planned: 88.2, actual: 86.5 },
  { week: 24, planned: 91.8, actual: 89.2 },
  { week: 25, planned: 95.5, actual: 92.8 },
  { week: 26, planned: 98.2, actual: 95.5 }
];

/**
 * Small dataset untuk quick testing (10 rows, 12 weeks)
 */
export const smallDataset = {
  rows: sampleHierarchyRows.slice(0, 10),
  weeks: sampleWeekColumns.slice(0, 12),
  planned: {
    2: samplePlannedProgress[2],
    3: samplePlannedProgress[3],
    4: samplePlannedProgress[4],
    7: samplePlannedProgress[7],
    8: samplePlannedProgress[8]
  },
  actual: {
    2: sampleActualProgress[2],
    3: sampleActualProgress[3],
    4: sampleActualProgress[4],
    7: sampleActualProgress[7],
    8: sampleActualProgress[8]
  },
  kurvaS: sampleKurvaSData.slice(0, 12)
};

/**
 * Medium dataset untuk integration testing (30 rows, 26 weeks)
 */
export const mediumDataset = {
  rows: sampleHierarchyRows,
  weeks: sampleWeekColumns,
  planned: samplePlannedProgress,
  actual: sampleActualProgress,
  kurvaS: sampleKurvaSData
};

/**
 * Large dataset generator untuk performance testing
 * @param {number} rowCount - Total rows to generate
 * @param {number} weekCount - Total weeks to generate
 * @returns {Object} Large dataset
 */
export function generateLargeDataset(rowCount = 100, weekCount = 52) {
  const rows = [];
  const planned = {};
  const actual = {};
  const weeks = [];
  const kurvaS = [];

  // Generate rows (klasifikasi + pekerjaan only, no sub-klasifikasi)
  let currentId = 1;
  const klasifikasiCount = Math.floor(rowCount / 10); // 10 pekerjaan per klasifikasi

  for (let k = 0; k < klasifikasiCount; k++) {
    rows.push({
      id: currentId++,
      type: 'klasifikasi',
      level: 0,
      parentId: null,
      name: `Klasifikasi ${k + 1}`
    });

    const klasifikasiId = currentId - 1;

    for (let p = 0; p < 10 && rows.length < rowCount; p++) {
      const pekerjaanId = currentId++;
      rows.push({
        id: pekerjaanId,
        type: 'pekerjaan',
        level: 1,
        parentId: klasifikasiId,
        name: `Pekerjaan ${k + 1}.${p + 1}`
      });

      // Generate progress (random but progressive)
      planned[pekerjaanId] = {};
      actual[pekerjaanId] = {};

      const startWeek = Math.floor(Math.random() * (weekCount - 10));
      const duration = 5 + Math.floor(Math.random() * 10); // 5-15 weeks

      for (let w = startWeek; w < Math.min(startWeek + duration, weekCount); w++) {
        const progress = Math.min(100, ((w - startWeek + 1) / duration) * 100);
        planned[pekerjaanId][w + 1] = Math.round(progress);
        actual[pekerjaanId][w + 1] = Math.round(progress * (0.8 + Math.random() * 0.2)); // 80-100% of planned
      }
    }
  }

  // Generate weeks
  const startDate = new Date('2025-01-06T00:00:00Z');
  for (let w = 0; w < weekCount; w++) {
    const weekStart = new Date(startDate);
    weekStart.setDate(startDate.getDate() + w * 7);

    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6);
    weekEnd.setHours(23, 59, 59);

    weeks.push({
      week: w + 1,
      startDate: weekStart.toISOString(),
      endDate: weekEnd.toISOString()
    });
  }

  // Generate cumulative Kurva S
  for (let w = 0; w < weekCount; w++) {
    const week = w + 1;
    let totalPlanned = 0;
    let totalActual = 0;
    let count = 0;

    Object.keys(planned).forEach(pekerjaanId => {
      if (planned[pekerjaanId][week]) {
        totalPlanned += planned[pekerjaanId][week];
        totalActual += actual[pekerjaanId][week] || 0;
        count++;
      }
    });

    kurvaS.push({
      week,
      planned: count > 0 ? Math.round((totalPlanned / count) * 10) / 10 : 0,
      actual: count > 0 ? Math.round((totalActual / count) * 10) / 10 : 0
    });
  }

  return { rows, weeks, planned, actual, kurvaS };
}
