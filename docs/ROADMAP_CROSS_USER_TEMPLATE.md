# 🗺️ ROADMAP: Cross-User Template Feature

**Status**: 📋 Planned (Not Implemented)
**Priority**: Medium
**Estimated Effort**: 3-4 weeks
**Dependencies**: FASE 3.1 (Deep Copy Core)

---

## 📖 Overview

### What is Cross-User Template?

**Cross-User Template** memungkinkan user untuk **share dan copy project antar users**:

```
User A (creator) → Create Project → Mark as "Shared Template"
                          ↓
                   Template Gallery (public/private)
                          ↓
User B (consumer) → Browse Templates → Copy to My Projects
```

### Key Differences from Regular Copy

| Feature | Regular Copy | Cross-User Template |
|---------|--------------|---------------------|
| **Source** | Own projects | Other users' projects |
| **Visibility** | Private | Public/Shared |
| **Permission** | Full access | Read-only template |
| **Ownership** | Same user | Different users |
| **Metadata** | Simple copy | Template info + usage tracking |

---

## 🏗️ Architecture Design

### Current Architecture Support

✅ **ARSITEKTUR SUDAH SIAP** untuk cross-user copy:

1. **User Isolation**: All models have `project` FK → `dashboard.Project.owner`
2. **Deep Copy Service**: Can copy all data regardless of owner
3. **No Hard-Coded Owner Checks**: Copy logic owner-agnostic

### Required Additions

#### 1. ProjectTemplate Model

```python
# dashboard/models.py

class ProjectTemplate(models.Model):
    """
    Public/shared templates untuk cross-user project copying.
    """
    # Source project
    source_project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='shared_templates'
    )

    # Template metadata
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=100,
        choices=[
            ('jalan', 'Jalan & Jembatan'),
            ('gedung', 'Gedung & Bangunan'),
            ('irigasi', 'Irigasi & Drainase'),
            ('mekanikal', 'Mekanikal & Elektrikal'),
            ('other', 'Lainnya'),
        ]
    )
    tags = models.JSONField(
        default=list,
        help_text='Tags untuk searchability (e.g., ["infrastruktur", "2_lantai"])'
    )

    # Visibility & permissions
    visibility = models.CharField(
        max_length=20,
        choices=[
            ('public', 'Public - Anyone can see & copy'),
            ('org', 'Organization - Only org members'),
            ('private', 'Private - Only invited users'),
        ],
        default='public'
    )

    # Creator & permissions
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_templates'
    )
    allowed_users = models.ManyToManyField(
        User,
        blank=True,
        related_name='accessible_templates',
        help_text='Users with explicit access (for private templates)'
    )

    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    thumbnail = models.ImageField(
        upload_to='template_thumbnails/',
        blank=True,
        null=True,
        help_text='Preview image for template gallery'
    )
    is_featured = models.BooleanField(
        default=False,
        help_text='Featured templates shown prominently'
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['visibility', '-usage_count']),
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['created_by', '-created_at']),
        ]

    def __str__(self):
        return f"{self.name} (by {self.created_by.username})"

    def can_access(self, user):
        """Check if user can access this template"""
        if self.visibility == 'public':
            return True
        if self.created_by == user:
            return True
        if self.visibility == 'private':
            return self.allowed_users.filter(id=user.id).exists()
        # Organization check (future)
        return False

    def increment_usage(self):
        """Track template usage"""
        from django.utils import timezone
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])
```

#### 2. TemplateUsageLog Model (Optional - Analytics)

```python
class TemplateUsageLog(models.Model):
    """
    Track who copied which template when (for analytics).
    """
    template = models.ForeignKey(
        ProjectTemplate,
        on_delete=models.CASCADE,
        related_name='usage_logs'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='template_usage'
    )
    copied_project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='The new project created from template'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
```

---

## 🎨 UI/UX Design

### 1. Template Gallery Page

**URL**: `/dashboard/templates/`

**Features**:
- Grid view dengan thumbnail
- Filter by category, tags
- Search by name, description
- Sort by: Popular, Recent, Featured
- "Use Template" button

### 2. Create Template Modal

**Trigger**: From project detail page → "Share as Template" button

**Form Fields**:
- Template Name
- Description
- Category (dropdown)
- Tags (multi-select)
- Visibility (public/org/private)
- Thumbnail upload (optional)

### 3. Template Detail Page

**URL**: `/dashboard/templates/{id}/`

**Display**:
- Full project preview (read-only)
- Creator info
- Usage count
- Category & tags
- "Copy to My Projects" button

---

## 🔧 Implementation Tasks

### Phase 1: Database & Models (1 week)
- [ ] Create ProjectTemplate model
- [ ] Create TemplateUsageLog model
- [ ] Migration
- [ ] Admin interface
- [ ] Write model tests (95%+ coverage)

### Phase 2: Template Management (1 week)
- [ ] Create template from project API
- [ ] Update template metadata API
- [ ] Delete template API
- [ ] Visibility & permission checks
- [ ] Write API tests

### Phase 3: Template Gallery (1 week)
- [ ] Template listing page
- [ ] Filter & search functionality
- [ ] Template detail page
- [ ] Thumbnail upload & processing
- [ ] Write UI tests

### Phase 4: Template Copy Integration (3-4 days)
- [ ] Integrate with Deep Copy Service (FASE 3.1)
- [ ] Copy template → new project
- [ ] Track usage & analytics
- [ ] Write integration tests

### Phase 5: Advanced Features (Optional - 1 week)
- [ ] Template versioning
- [ ] Template ratings & reviews
- [ ] Template collections/bundles
- [ ] Organization-level templates

---

## 🔐 Security Considerations

### Permission Checks

```python
# Example permission check
def copy_template(template_id, user):
    template = ProjectTemplate.objects.get(id=template_id)

    # Check access permission
    if not template.can_access(user):
        raise PermissionDenied("You don't have access to this template")

    # Copy source project to new project owned by current user
    new_project = deep_copy_service.copy_project(
        source_project=template.source_project,
        new_owner=user,  # Different owner!
        new_name=f"{template.name} (Copy)"
    )

    # Track usage
    template.increment_usage()
    TemplateUsageLog.objects.create(
        template=template,
        user=user,
        copied_project=new_project
    )

    return new_project
```

### Data Privacy

1. **Sensitive Data Removal**: Option to exclude sensitive fields when creating template
2. **Audit Trail**: Log all template access & copying
3. **GDPR Compliance**: Allow template creators to delete templates + all copies tracking

---

## 📊 Success Metrics

| Metric | Target |
|--------|--------|
| **Template Adoption** | 30% users create ≥1 template in first 3 months |
| **Template Usage** | 50% new projects from templates after 6 months |
| **Popular Templates** | Top 10 templates used 100+ times each |
| **User Satisfaction** | 4.5/5 rating for template feature |

---

## 🚀 Future Enhancements

1. **Template Marketplace**: Paid premium templates
2. **AI-Powered Recommendations**: Suggest templates based on project type
3. **Collaborative Templates**: Multiple users can edit template
4. **Template Import/Export**: Share templates via JSON/ZIP files
5. **Template Diff Viewer**: Compare template versions

---

## ✅ Architecture Verification

### Can Current Architecture Support This?

**YES** ✅ - Current architecture is ready:

| Requirement | Current Support | Notes |
|-------------|-----------------|-------|
| **User Isolation** | ✅ Yes | All models have `project.owner` FK |
| **Deep Copy** | ✅ Yes | FASE 3.1 implements this |
| **Permission System** | ✅ Yes | Django auth + custom checks |
| **Cross-User FK** | ✅ Yes | No hard-coded owner validation |
| **Audit Trail** | ✅ Yes | TimeStampedModel mixin |

### Required Changes to Deep Copy Service

**NONE** - Deep Copy Service (FASE 3.1) already supports different owners:

```python
# Example from FASE 3.1 (to be implemented)
def deep_copy_project(source_project, new_owner, new_name):
    """
    Copy project with all related data.

    Args:
        source_project: Project to copy (any owner)
        new_owner: User who will own the new project
        new_name: Name for new project
    """
    # This already works regardless of owner!
    new_project = Project.objects.create(
        owner=new_owner,  # Different owner OK!
        nama=new_name,
        # ... copy other fields
    )
    # Copy all related data...
```

---

## 📝 Conclusion

**Cross-User Template feature is ARCHITECTURALLY READY** untuk implementation di masa depan.

Current FASE 3.1 (Deep Copy Core) sudah menyediakan semua foundation yang diperlukan. Template feature hanya perlu:
1. UI layer (gallery, detail)
2. Permission layer (visibility checks)
3. Metadata layer (ProjectTemplate model)

**Recommendation**: Implement FASE 3.1 first, deploy to production, gather user feedback, then prioritize Template feature based on demand.
