/**
 * Gantt Chart Data Model
 * Hierarchical data structure for Klasifikasi → Sub-Klasifikasi → Pekerjaan
 * @module gantt-data-model
 */

/**
 * Base Node - shared properties for all node types
 */
class BaseNode {
  constructor(data) {
    this.id = data.id;
    this.name = data.name;
    this.expanded = data.expanded !== undefined ? data.expanded : true;
    this.visible = true;
    this.level = 0;
    this.parentId = null;
  }

  /**
   * Toggle expand/collapse state
   */
  toggleExpand() {
    this.expanded = !this.expanded;
    return this.expanded;
  }

  /**
   * Check if node is leaf (no children)
   */
  isLeaf() {
    return false;
  }
}

/**
 * Task Bar - represents planned or actual timeline
 */
export class TaskBar {
  constructor(data = {}) {
    this.startDate = data.startDate ? new Date(data.startDate) : null;
    this.endDate = data.endDate ? new Date(data.endDate) : null;
    this.progress = data.progress || 0; // 0-100
    this.duration = data.duration || 0; // in days
  }

  /**
   * Calculate duration in days
   */
  calculateDuration() {
    if (!this.startDate || !this.endDate) return 0;
    const diffTime = Math.abs(this.endDate - this.startDate);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  }

  /**
   * Check if bar is valid
   */
  isValid() {
    return this.startDate && this.endDate && this.startDate <= this.endDate;
  }

  /**
   * Get progress date (where progress bar ends)
   */
  getProgressDate() {
    if (!this.isValid() || this.progress === 0) return this.startDate;
    const duration = this.calculateDuration();
    const progressDays = Math.floor((duration * this.progress) / 100);
    const progressDate = new Date(this.startDate);
    progressDate.setDate(progressDate.getDate() + progressDays);
    return progressDate;
  }
}

/**
 * Pekerjaan Node - leaf node with planned and actual bars
 */
export class PekerjaanNode extends BaseNode {
  constructor(data) {
    super(data);
    this.type = 'pekerjaan';
    this.kode = data.kode || '';

    // Dual bars
    this.planned = new TaskBar({
      startDate: data.tgl_mulai_rencana,
      endDate: data.tgl_selesai_rencana,
      progress: data.progress_rencana || 0
    });

    this.actual = new TaskBar({
      startDate: data.tgl_mulai_realisasi,
      endDate: data.tgl_selesai_realisasi,
      progress: data.progress_realisasi || 0
    });

    // Status calculation
    this.status = this._calculateStatus();

    // Volume & satuan
    this.volume = data.volume || 0;
    this.satuan = data.satuan || '';

    // References
    this.subKlasifikasiId = data.sub_klasifikasi_id;
    this.klasifikasiId = data.klasifikasi_id;
  }

  /**
   * Calculate status based on dates and progress
   */
  _calculateStatus() {
    const now = new Date();

    // Not started if no actual start date
    if (!this.actual.startDate) {
      return 'not-started';
    }

    // Completed if progress is 100%
    if (this.actual.progress === 100) {
      return 'complete';
    }

    // In progress if started but not complete
    if (this.actual.startDate <= now) {
      // Check if delayed (actual progress < planned progress)
      if (this.actual.progress < this.planned.progress) {
        return 'delayed';
      }
      return 'in-progress';
    }

    return 'not-started';
  }

  /**
   * Update status
   */
  updateStatus() {
    this.status = this._calculateStatus();
  }

  /**
   * Check if node is leaf
   */
  isLeaf() {
    return true;
  }

  /**
   * Get earliest start date
   */
  getStartDate() {
    const dates = [this.planned.startDate, this.actual.startDate].filter(d => d);
    if (dates.length === 0) return null;
    return new Date(Math.min(...dates));
  }

  /**
   * Get latest end date
   */
  getEndDate() {
    const dates = [this.planned.endDate, this.actual.endDate].filter(d => d);
    if (dates.length === 0) return null;
    return new Date(Math.max(...dates));
  }
}

/**
 * Sub-Klasifikasi Node - middle level
 */
export class SubKlasifikasiNode extends BaseNode {
  constructor(data) {
    super(data);
    this.type = 'sub-klasifikasi';
    this.kode = data.kode || '';
    this.pekerjaan = [];
    this.klasifikasiId = data.klasifikasi_id;
    this.level = 2;
  }

  /**
   * Add pekerjaan
   */
  addPekerjaan(pekerjaan) {
    pekerjaan.level = 3;
    pekerjaan.parentId = this.id;
    this.pekerjaan.push(pekerjaan);
  }

  /**
   * Get all pekerjaan
   */
  getPekerjaan() {
    return this.pekerjaan;
  }

  /**
   * Get pekerjaan count
   */
  getPekerjaanCount() {
    return this.pekerjaan.length;
  }

  /**
   * Calculate aggregated progress
   */
  getAggregatedProgress(mode = 'planned') {
    if (this.pekerjaan.length === 0) return 0;

    const totalProgress = this.pekerjaan.reduce((sum, p) => {
      return sum + (mode === 'planned' ? p.planned.progress : p.actual.progress);
    }, 0);

    return Math.round(totalProgress / this.pekerjaan.length);
  }

  /**
   * Get date range (earliest start to latest end)
   */
  getDateRange() {
    if (this.pekerjaan.length === 0) return { start: null, end: null };

    const startDates = this.pekerjaan
      .map(p => p.getStartDate())
      .filter(d => d);

    const endDates = this.pekerjaan
      .map(p => p.getEndDate())
      .filter(d => d);

    return {
      start: startDates.length > 0 ? new Date(Math.min(...startDates)) : null,
      end: endDates.length > 0 ? new Date(Math.max(...endDates)) : null
    };
  }

  /**
   * Check if node is leaf
   */
  isLeaf() {
    return this.pekerjaan.length === 0;
  }
}

/**
 * Klasifikasi Node - top level
 */
export class KlasifikasiNode extends BaseNode {
  constructor(data) {
    super(data);
    this.type = 'klasifikasi';
    this.kode = data.kode || '';
    this.subKlasifikasi = [];
    this.level = 1;
  }

  /**
   * Add sub-klasifikasi
   */
  addSubKlasifikasi(subKlasifikasi) {
    subKlasifikasi.level = 2;
    subKlasifikasi.parentId = this.id;
    this.subKlasifikasi.push(subKlasifikasi);
  }

  /**
   * Get all sub-klasifikasi
   */
  getSubKlasifikasi() {
    return this.subKlasifikasi;
  }

  /**
   * Get all pekerjaan (flattened from all sub-klasifikasi)
   */
  getAllPekerjaan() {
    return this.subKlasifikasi.flatMap(sub => sub.getPekerjaan());
  }

  /**
   * Get total pekerjaan count
   */
  getTotalPekerjaanCount() {
    return this.subKlasifikasi.reduce((sum, sub) => {
      return sum + sub.getPekerjaanCount();
    }, 0);
  }

  /**
   * Calculate aggregated progress
   */
  getAggregatedProgress(mode = 'planned') {
    const allPekerjaan = this.getAllPekerjaan();
    if (allPekerjaan.length === 0) return 0;

    const totalProgress = allPekerjaan.reduce((sum, p) => {
      return sum + (mode === 'planned' ? p.planned.progress : p.actual.progress);
    }, 0);

    return Math.round(totalProgress / allPekerjaan.length);
  }

  /**
   * Get date range
   */
  getDateRange() {
    if (this.subKlasifikasi.length === 0) return { start: null, end: null };

    const ranges = this.subKlasifikasi.map(sub => sub.getDateRange());
    const startDates = ranges.map(r => r.start).filter(d => d);
    const endDates = ranges.map(r => r.end).filter(d => d);

    return {
      start: startDates.length > 0 ? new Date(Math.min(...startDates)) : null,
      end: endDates.length > 0 ? new Date(Math.max(...endDates)) : null
    };
  }

  /**
   * Check if node is leaf
   */
  isLeaf() {
    return this.subKlasifikasi.length === 0;
  }
}

/**
 * Milestone - marks important dates with comments
 */
export class Milestone {
  constructor(data) {
    this.id = data.id || this._generateId();
    this.date = new Date(data.date);
    this.title = data.title || '';
    this.description = data.description || '';
    this.color = data.color || '#ff6b6b';
    this.icon = data.icon || '📍';
    this.comments = data.comments || [];
    this.linkedPekerjaan = data.linkedPekerjaan || []; // Array of pekerjaan IDs
    this.createdAt = data.createdAt ? new Date(data.createdAt) : new Date();
    this.createdBy = data.createdBy || '';
  }

  /**
   * Generate unique ID
   */
  _generateId() {
    return `milestone_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Add comment
   */
  addComment(comment) {
    this.comments.push({
      id: `comment_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      text: comment.text,
      author: comment.author || '',
      timestamp: new Date()
    });
  }

  /**
   * Remove comment
   */
  removeComment(commentId) {
    this.comments = this.comments.filter(c => c.id !== commentId);
  }

  /**
   * Link pekerjaan
   */
  linkPekerjaan(pekerjaanId) {
    if (!this.linkedPekerjaan.includes(pekerjaanId)) {
      this.linkedPekerjaan.push(pekerjaanId);
    }
  }

  /**
   * Unlink pekerjaan
   */
  unlinkPekerjaan(pekerjaanId) {
    this.linkedPekerjaan = this.linkedPekerjaan.filter(id => id !== pekerjaanId);
  }
}

/**
 * Project Metadata
 */
export class ProjectMetadata {
  constructor(data) {
    this.projectId = data.project_id;
    this.projectName = data.project_name || '';
    this.startDate = new Date(data.start_date);
    this.endDate = new Date(data.end_date);
    this.currentDate = new Date();
  }

  /**
   * Get project duration in days
   */
  getDuration() {
    const diffTime = Math.abs(this.endDate - this.startDate);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }

  /**
   * Get progress percentage based on time elapsed
   */
  getTimeProgress() {
    const total = this.endDate - this.startDate;
    const elapsed = this.currentDate - this.startDate;
    return Math.round((elapsed / total) * 100);
  }
}

/**
 * Main Gantt Data Model
 */
export class GanttDataModel {
  constructor() {
    this.klasifikasi = [];
    this.milestones = [];
    this.projectMeta = null;
    this._flattenedNodes = null; // Cache for flattened tree
    this._nodeIndex = new Map(); // Quick lookup by ID
  }

  /**
   * Initialize from raw data
   */
  initialize(rawData) {
    console.log('📊 Initializing Gantt Data Model...');

    // Project metadata
    this.projectMeta = new ProjectMetadata(rawData.project);

    // Build hierarchy
    this._buildHierarchy(rawData.data);

    // Load milestones
    if (rawData.milestones) {
      this.milestones = rawData.milestones.map(m => new Milestone(m));
    }

    // Build index
    this._buildNodeIndex();

    console.log(`✅ Gantt Data Model initialized: ${this.klasifikasi.length} klasifikasi, ${this.getTotalPekerjaanCount()} pekerjaan`);
  }

  /**
   * Build hierarchy from flat data
   */
  _buildHierarchy(flatData) {
    // Group by klasifikasi
    const klasifikasiMap = new Map();
    const subKlasifikasiMap = new Map();

    // First pass: create all nodes
    flatData.forEach(row => {
      // Create/get klasifikasi
      if (!klasifikasiMap.has(row.klasifikasi_id)) {
        klasifikasiMap.set(row.klasifikasi_id, new KlasifikasiNode({
          id: row.klasifikasi_id,
          name: row.klasifikasi_name,
          kode: row.klasifikasi_kode
        }));
      }

      // Create/get sub-klasifikasi
      if (!subKlasifikasiMap.has(row.sub_klasifikasi_id)) {
        const subKlasifikasi = new SubKlasifikasiNode({
          id: row.sub_klasifikasi_id,
          name: row.sub_klasifikasi_name,
          kode: row.sub_klasifikasi_kode,
          klasifikasi_id: row.klasifikasi_id
        });
        subKlasifikasiMap.set(row.sub_klasifikasi_id, subKlasifikasi);
      }

      // Create pekerjaan
      const pekerjaan = new PekerjaanNode({
        id: row.pekerjaan_id,
        name: row.pekerjaan_name,
        kode: row.pekerjaan_kode,
        tgl_mulai_rencana: row.tgl_mulai_rencana,
        tgl_selesai_rencana: row.tgl_selesai_rencana,
        tgl_mulai_realisasi: row.tgl_mulai_realisasi,
        tgl_selesai_realisasi: row.tgl_selesai_realisasi,
        progress_rencana: row.progress_rencana,
        progress_realisasi: row.progress_realisasi,
        volume: row.volume,
        satuan: row.satuan,
        sub_klasifikasi_id: row.sub_klasifikasi_id,
        klasifikasi_id: row.klasifikasi_id
      });

      // Add to parent
      subKlasifikasiMap.get(row.sub_klasifikasi_id).addPekerjaan(pekerjaan);
    });

    // Second pass: build tree
    subKlasifikasiMap.forEach(subKlasifikasi => {
      const klasifikasi = klasifikasiMap.get(subKlasifikasi.klasifikasiId);
      if (klasifikasi) {
        klasifikasi.addSubKlasifikasi(subKlasifikasi);
      }
    });

    // Store as array
    this.klasifikasi = Array.from(klasifikasiMap.values());
  }

  /**
   * Build node index for quick lookup
   */
  _buildNodeIndex() {
    this._nodeIndex.clear();

    this.klasifikasi.forEach(klas => {
      this._nodeIndex.set(klas.id, klas);

      klas.getSubKlasifikasi().forEach(sub => {
        this._nodeIndex.set(sub.id, sub);

        sub.getPekerjaan().forEach(pek => {
          this._nodeIndex.set(pek.id, pek);
        });
      });
    });
  }

  /**
   * Get node by ID
   */
  getNodeById(nodeId) {
    return this._nodeIndex.get(nodeId);
  }

  /**
   * Get flattened tree (respecting expand/collapse state)
   */
  getFlattenedTree() {
    const flattened = [];

    this.klasifikasi.forEach(klas => {
      flattened.push(klas);

      if (klas.expanded) {
        klas.getSubKlasifikasi().forEach(sub => {
          flattened.push(sub);

          if (sub.expanded) {
            sub.getPekerjaan().forEach(pek => {
              flattened.push(pek);
            });
          }
        });
      }
    });

    return flattened;
  }

  /**
   * Toggle node expand state
   */
  toggleNode(nodeId) {
    const node = this.getNodeById(nodeId);
    if (node && !node.isLeaf()) {
      node.toggleExpand();
      this._flattenedNodes = null; // Invalidate cache
      return node.expanded;
    }
    return null;
  }

  /**
   * Get total pekerjaan count
   */
  getTotalPekerjaanCount() {
    return this.klasifikasi.reduce((sum, klas) => {
      return sum + klas.getTotalPekerjaanCount();
    }, 0);
  }

  /**
   * Get project date range
   */
  getProjectDateRange() {
    if (!this.projectMeta) return { start: null, end: null };
    return {
      start: this.projectMeta.startDate,
      end: this.projectMeta.endDate
    };
  }

  /**
   * Add milestone
   */
  addMilestone(milestoneData) {
    const milestone = new Milestone(milestoneData);
    this.milestones.push(milestone);
    return milestone;
  }

  /**
   * Remove milestone
   */
  removeMilestone(milestoneId) {
    this.milestones = this.milestones.filter(m => m.id !== milestoneId);
  }

  /**
   * Get milestone by ID
   */
  getMilestoneById(milestoneId) {
    return this.milestones.find(m => m.id === milestoneId);
  }

  /**
   * Get milestones in date range
   */
  getMilestonesInRange(startDate, endDate) {
    return this.milestones.filter(m => {
      return m.date >= startDate && m.date <= endDate;
    });
  }

  /**
   * Search nodes by text
   */
  searchNodes(searchText) {
    const lowerSearch = searchText.toLowerCase();
    const results = [];

    this.klasifikasi.forEach(klas => {
      if (klas.name.toLowerCase().includes(lowerSearch) ||
          klas.kode.toLowerCase().includes(lowerSearch)) {
        results.push(klas);
      }

      klas.getSubKlasifikasi().forEach(sub => {
        if (sub.name.toLowerCase().includes(lowerSearch) ||
            sub.kode.toLowerCase().includes(lowerSearch)) {
          results.push(sub);
        }

        sub.getPekerjaan().forEach(pek => {
          if (pek.name.toLowerCase().includes(lowerSearch) ||
              pek.kode.toLowerCase().includes(lowerSearch)) {
            results.push(pek);
          }
        });
      });
    });

    return results;
  }

  /**
   * Export to JSON
   */
  toJSON() {
    return {
      klasifikasi: this.klasifikasi,
      milestones: this.milestones,
      projectMeta: this.projectMeta
    };
  }
}

export default GanttDataModel;
