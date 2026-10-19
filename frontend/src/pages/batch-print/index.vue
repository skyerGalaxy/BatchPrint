<template>
  <v-container fluid class="batch-shell px-6 py-6">
    <v-row class="batch-grid" align="stretch" no-gutters>
      <v-col cols="12" lg="4" class="batch-col pe-lg-3">
        <div class="control-card">
          <div class="card-header">
            <v-icon size="20" color="primary" class="mr-2">mdi-tune-variant</v-icon>
            <span class="card-title">输入输出设置</span>
            <v-spacer></v-spacer>
            <v-btn
              v-if="hasAnyPath"
              variant="text"
              color="grey-darken-1"
              size="small"
              rounded="lg"
              :loading="reloading"
              @click="reloadFromPaths"
            >
              <v-icon size="16" class="mr-1">mdi-reload</v-icon>
              重新加载
            </v-btn>
            <v-btn
              variant="text"
              color="grey-darken-1"
              size="small"
              rounded="lg"
              @click="requestReset"
            >
              <v-icon size="16" class="mr-1">mdi-refresh</v-icon>
              重置
            </v-btn>
          </div>

          <div class="control-body">
            <div class="section">
              <div class="section-label">模板</div>
              <v-btn
                variant="outlined"
                block
                rounded="lg"
                prepend-icon="mdi-file-document-outline"
                class="pick-file-btn"
                @click="pickTemplate"
              >
                选择模板（PDF / DOCX）
              </v-btn>
              <div v-if="templatePath" class="file-picked-hint">
                <v-icon size="14" color="success">mdi-check-circle-outline</v-icon>
                <span class="file-picked-name" :title="templatePath">{{ templateFileName }}</span>
              </div>
              <div v-if="templatePath" class="file-meta-row">
                <span>{{ templateMtimeText }}</span>
              </div>
            </div>

            <div class="section">
              <div class="section-label">表格</div>
              <v-btn
                variant="outlined"
                block
                rounded="lg"
                prepend-icon="mdi-file-excel"
                class="pick-file-btn"
                @click="pickExcel"
              >
                选择 Excel 数据
              </v-btn>
              <div v-if="excelPath" class="file-picked-hint">
                <v-icon size="14" color="success">mdi-check-circle-outline</v-icon>
                <span class="file-picked-name" :title="excelPath">{{ excelFileName }}</span>
              </div>
              <div v-if="excelPath" class="file-meta-row">
                <span>{{ excelMtimeText }}</span>
              </div>
            </div>

            <div class="section field-section">
              <div class="section-label">材料</div>
              <div class="material-nav" @mouseleave="clearHoverTimer">
                <button
                  v-for="item in materialNavItems"
                  :key="item.value"
                  type="button"
                  class="material-nav-item"
                  :class="[
                    `material-nav-item--${item.value}`,
                    { active: activeMaterialNav === item.value }
                  ]"
                  @mouseenter="setActiveNav(item.value)"
                  @focus="setActiveNav(item.value)"
                  @click="activeMaterialNav = item.value"
                >
                  <v-icon size="18">{{ item.icon }}</v-icon>
                  <span>{{ item.title }}</span>
                </button>
              </div>
              <div class="material-expand-host">
                <Transition name="material-fade" mode="out-in">
                  <div :key="activeMaterialNav" class="material-stage-inner">
                  <!-- 表格：解析 Excel 的字段 -->
                  <template v-if="activeMaterialNav === 'table'">
                    <div v-if="bpStore.fieldNames.length === 0" class="expand-empty-tip">
                      请先选择 Excel 文件
                    </div>
                    <div v-else class="field-chip-list">
                      <div
                        v-for="item in bpStore.fieldNames"
                        :key="item"
                        class="field-chip"
                        draggable="true"
                        @dragstart="startFieldDrag($event, item)"
                      >
                        {{ item }}
                      </div>
                    </div>
                  </template>

                  <!-- 签字：设置路径下的签字内容 -->
                  <template v-else-if="activeMaterialNav === 'signature'">
                    <div class="thumb-grid">
                      <div
                        v-for="(img, idx) in bpStore.imageList_signature"
                        :key="idx"
                        class="thumb-card thumb-card--signature"
                        draggable="true"
                        @dragstart="startImageDrag($event, 'signature', idx)"
                        @contextmenu.prevent="onImageContextMenu($event, 'signature', idx)"
                      >
                        <img :src="img" />
                      </div>
                      <button
                        type="button"
                        class="thumb-card thumb-add thumb-add--signature"
                        title="添加签字图片"
                        @click="triggerImagePicker('signature')"
                      >
                        <v-icon size="28">mdi-plus</v-icon>
                      </button>
                    </div>
                  </template>

                  <!-- 印章：设置路径下的印章内容 -->
                  <template v-else-if="activeMaterialNav === 'seal'">
                    <div class="thumb-grid">
                      <div
                        v-for="(img, idx) in bpStore.imageList_seal"
                        :key="idx"
                        class="thumb-card thumb-card--seal"
                        draggable="true"
                        @dragstart="startImageDrag($event, 'seal', idx)"
                        @contextmenu.prevent="onImageContextMenu($event, 'seal', idx)"
                      >
                        <img :src="img" />
                      </div>
                      <button
                        type="button"
                        class="thumb-card thumb-add thumb-add--seal"
                        title="添加印章图片"
                        @click="triggerImagePicker('seal')"
                      >
                        <v-icon size="28">mdi-plus</v-icon>
                      </button>
                    </div>
                  </template>

                  <!-- 图标：预设图标 -->
                  <template v-else-if="activeMaterialNav === 'icon'">
                    <div class="icon-mini-grid">
                      <div
                        v-for="g in iconGroups"
                        :key="g.value"
                        class="icon-mini-group"
                      >
                        <div class="icon-mini-label">{{ g.label }}</div>
                        <div class="icon-mini-row">
                          <div
                            v-for="ic in g.icons"
                            :key="ic.char"
                            class="icon-mini-cell"
                            :title="ic.label"
                            draggable="true"
                            @dragstart="startIconDrag($event, ic.char)"
                          >
                            {{ ic.char }}
                          </div>
                        </div>
                      </div>
                    </div>
                  </template>

                  <!-- 文本：预设文本 chips，+ chip 打开文本窗口添加自定义文字 -->
                  <template v-else-if="activeMaterialNav === 'text'">
                    <div class="text-preset-list">
                      <div
                        v-for="preset in textPresets"
                        :key="preset.id"
                        class="text-preset-chip"
                        :title="`点击编辑，或拖动「${preset.text}」到 PDF`"
                        draggable="true"
                        @dragstart="startPresetTextDrag($event, preset)"
                        @dragend="handlePresetDragEnd"
                        @click="openPresetEditor(preset)"
                      >
                        <span class="text-preset-label" :style="presetPreviewStyle(preset)">
                          {{ preset.text }}
                        </span>
                        <button
                          type="button"
                          class="text-preset-del"
                          title="删除预设"
                          @click.stop="deleteTextPreset(preset.id)"
                        >
                          <v-icon size="12">mdi-close</v-icon>
                        </button>
                      </div>
                      <button type="button" class="text-preset-add" @click="openTextDialog()">
                        <v-icon size="16">mdi-plus</v-icon>
                        <span>添加文本</span>
                      </button>
                    </div>
                  </template>
                  </div>
                </Transition>
              </div>
            </div>

            <div class="section filename-section">
              <div class="section-label">文件名</div>

              <div
                ref="nameInputRef"
                class="name-input"
                tabindex="0"
                @click.self="setInsert(nameParts.length)"
                @keydown="handleNameKeydown"
              >
                <template v-for="(part, i) in nameParts" :key="i">
                  <span
                    class="insert-gap"
                    :class="{ 'insert-gap--active': insertIndex === i }"
                    @click.stop="setInsert(i)"
                  ></span>
                  <v-chip
                    :color="partColors[part.type]"
                    :variant="part.type === 'sep' ? 'outlined' : 'tonal'"
                    size="small"
                    closable
                    @click.stop="setInsert(i + 1)"
                    @click:close="removeNamePart(i)"
                  >
                    <v-icon
                      v-if="part.type === 'field' || part.type === 'seq'"
                      start
                      size="12"
                    >
                      {{ partIcons[part.type] }}
                    </v-icon>
                    {{ partLabel(part) }}
                  </v-chip>
                </template>
                <span
                  v-if="nameParts.length > 0"
                  class="insert-gap"
                  :class="{ 'insert-gap--active': insertIndex === nameParts.length }"
                  @click.stop="setInsert(nameParts.length)"
                ></span>

                <span
                  v-if="nameParts.length === 0"
                  class="name-placeholder"
                  @click.stop="setInsert(0)"
                >
                  点击 + 组合文件名，默认按序号命名
                </span>

                <v-menu v-model="addMenuOpen" :close-on-content-click="false">
                  <template #activator="{ props }">
                    <v-btn
                      v-bind="props"
                      icon
                      size="x-small"
                      variant="tonal"
                      color="primary"
                      class="name-add-btn"
                    >
                      <v-icon size="16">mdi-plus</v-icon>
                    </v-btn>
                  </template>

                  <v-list density="compact" min-width="170">
                    <v-list-item :disabled="bpStore.fieldNames.length === 0">
                      <template #prepend>
                        <v-icon size="16">mdi-table-column</v-icon>
                      </template>
                      <v-list-item-title>字段</v-list-item-title>
                      <template #append>
                        <v-icon size="16">mdi-menu-right</v-icon>
                      </template>
                      <v-menu submenu activator="parent" open-on-hover>
                        <v-list density="compact" max-height="280">
                          <v-list-item
                            v-for="fieldName in bpStore.fieldNames"
                            :key="fieldName"
                            @click="addFieldPart(fieldName)"
                          >
                            <v-list-item-title>{{ fieldName }}</v-list-item-title>
                          </v-list-item>
                        </v-list>
                      </v-menu>
                    </v-list-item>

                    <v-list-item>
                      <template #prepend>
                        <v-icon size="16">mdi-numeric</v-icon>
                      </template>
                      <v-list-item-title>自增数字</v-list-item-title>
                      <template #append>
                        <v-icon size="16">mdi-menu-right</v-icon>
                      </template>
                      <v-menu submenu activator="parent" open-on-hover>
                        <v-list density="compact">
                          <v-list-item
                            v-for="opt in seqOptions"
                            :key="opt.digits"
                            @click="addSeqPart(opt.digits)"
                          >
                            <v-list-item-title>{{ opt.title }}</v-list-item-title>
                          </v-list-item>
                        </v-list>
                      </v-menu>
                    </v-list-item>

                    <v-list-item>
                      <template #prepend>
                        <v-icon size="16">mdi-format-text</v-icon>
                      </template>
                      <v-list-item-title>自定义文本</v-list-item-title>
                      <template #append>
                        <v-icon size="16">mdi-menu-right</v-icon>
                      </template>
                      <v-menu submenu activator="parent" :close-on-content-click="false">
                        <v-card class="pa-2" min-width="230">
                          <div class="d-flex align-center ga-2">
                            <v-text-field
                              v-model="customText"
                              density="compact"
                              variant="outlined"
                              hide-details
                              autofocus
                              placeholder="输入文本"
                              class="custom-text-input"
                              @keyup.enter="addTextPart"
                            />
                            <v-btn
                              size="small"
                              color="primary"
                              variant="tonal"
                              :disabled="!customText"
                              @click="addTextPart"
                            >
                              添加
                            </v-btn>
                          </div>
                        </v-card>
                      </v-menu>
                    </v-list-item>

                    <v-list-item>
                      <template #prepend>
                        <v-icon size="16">mdi-minus</v-icon>
                      </template>
                      <v-list-item-title>连接符</v-list-item-title>
                      <template #append>
                        <v-icon size="16">mdi-menu-right</v-icon>
                      </template>
                      <v-menu submenu activator="parent" open-on-hover>
                        <v-list density="compact">
                          <v-list-item
                            v-for="sep in sepOptions"
                            :key="sep.value"
                            @click="addSepPart(sep.value)"
                          >
                            <v-list-item-title>{{ sep.title }}</v-list-item-title>
                          </v-list-item>
                        </v-list>
                      </v-menu>
                    </v-list-item>
                  </v-list>
                </v-menu>
              </div>

              <div class="name-preview">
                <span class="preview-label">预览</span>
                <span class="path-mono">{{ fileNamePreview }}</span>
              </div>
            </div>

            <v-btn
              color="primary"
              size="large"
              rounded="lg"
              block
              class="generate-btn"
              :disabled="generating"
              @click="generateBatchPDF"
            >
              <v-icon size="18" class="mr-2">mdi-file-document-multiple</v-icon>
              {{ generating ? `生成中 ${generateCurrent}/${generateTotal}` : (bpStore.templateType === 'pdf' ? '生成 PDF' : '生成 DOCX') }}
            </v-btn>

            <div v-if="generating" class="generate-progress">
              <v-progress-linear
                :model-value="generateProgress"
                color="primary"
                height="8"
                rounded
                striped
                stream
              />
              <div class="generate-progress-text">
                <span>{{ bpStore.templateType === 'pdf' ? '正在生成 PDF…' : '正在生成 DOCX…' }}</span>
                <span>{{ generateCurrent }} / {{ generateTotal }}（{{ Math.round(generateProgress) }}%）</span>
              </div>
            </div>
          </div>
        </div>
      </v-col>

      <v-col cols="12" lg="8" class="batch-col ps-lg-3">
        <div class="preview-card">
          <div class="card-header preview-top">
            <div class="d-flex align-center">
              <v-icon size="20" color="primary" class="mr-2">mdi-eye-outline</v-icon>
              <span class="card-title">预览区</span>
            </div>
            <div class="d-flex align-center ga-2 preview-actions">
              <v-chip
                v-if="bpStore.currentProjectId"
                variant="tonal"
                size="small"
                color="primary"
                class="project-chip"
                :title="bpStore.currentProjectTitle"
              >
                <v-icon start size="13">mdi-folder-edit-outline</v-icon>
                <span class="project-chip-name">{{ bpStore.currentProjectTitle }}</span>
              </v-chip>
              <v-btn
                v-if="hasProjectHistory"
                icon
                size="small"
                variant="text"
                color="primary"
                class="history-icon-btn"
                @click="openProjectHistory"
              >
                <v-badge :content="bpStore.currentProjectRevisionCount" color="primary" offset-x="-2" offset-y="-2">
                  <v-icon size="19">mdi-history</v-icon>
                </v-badge>
                <v-tooltip activator="parent" location="bottom">查看项目历史</v-tooltip>
              </v-btn>
              <v-chip
                v-if="bpStore.templateType === 'pdf' && bpStore.iconList.length > 0"
                variant="outlined"
                size="small"
                color="grey"
                class="clear-chip"
                @click="requestClearIcons"
              >
                <v-icon start size="12">mdi-delete-outline</v-icon>
                清空标注 ({{ bpStore.iconList.length }})
              </v-chip>
              <v-btn
                v-if="hasTemplate"
                variant="tonal"
                size="small"
                color="primary"
                rounded="lg"
                class="save-progress-btn"
                :disabled="!canSaveProgress"
                @click="openSaveDialog"
              >
                <v-icon start size="14">mdi-content-save-outline</v-icon>
                {{ canSaveProgress ? '保存工作进度' : '暂无改动' }}
              </v-btn>
            </div>
          </div>

          <div class="preview-surface">
            <div class="preview-scroll">
              <PdfViewer v-if="bpStore.templateType === 'pdf'" :pdf-src="pdfSrc" />
              <DocxViewer
                v-else
                ref="docxViewerRef"
                @contextmenu-block="openLoopBlockDialog"
              />
            </div>
          </div>
        </div>
      </v-col>
    </v-row>

    <v-dialog v-model="resultDialog" max-width="440">
      <v-card rounded="xl" elevation="8">
        <v-card-item>
          <div class="d-flex align-center">
            <v-icon :color="resultSuccess ? 'success' : 'error'" size="28" class="mr-3">
              {{ resultSuccess ? 'mdi-check-circle' : 'mdi-alert-circle' }}
            </v-icon>
            <v-card-title class="pa-0">
              {{ resultSuccess ? '生成成功' : '提示' }}
            </v-card-title>
          </div>
        </v-card-item>
        <v-card-text>
          <p class="text-body-2 mb-4">{{ resultMessage }}</p>
          <div v-if="resultSuccess && resultPath" class="d-flex align-center ga-2">
            <span class="text-caption text-grey-darken-1">输出目录：</span>
            <code class="path-mono">{{ resultPath }}</code>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn
            v-if="resultSuccess && resultPath"
            variant="tonal"
            color="primary"
            rounded="lg"
            prepend-icon="mdi-folder-open-outline"
            @click="openFolder(resultPath)"
          >
            打开目录
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn variant="text" rounded="lg" @click="resultDialog = false">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="mergedCellsDialog" max-width="480">
      <v-card>
        <v-card-item>
          <v-card-title class="text-warning">
            <v-icon color="warning" class="mr-2">mdi-alert</v-icon>
            表格格式需要调整
          </v-card-title>
        </v-card-item>
        <v-card-text>
          <p>检测到 Excel 首行存在合并单元格，无法正确解析字段名。</p>
          <p>请取消合并首行单元格，确保每个字段独占一列，然后重新选择文件。</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="mergedCellsDialog = false">知道了</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="invalidFieldsDialog" max-width="480">
      <v-card>
        <v-card-item>
          <v-card-title class="text-warning">
            <v-icon color="warning" class="mr-2">mdi-alert</v-icon>
            字段已失效
          </v-card-title>
        </v-card-item>
        <v-card-text>
          <p>当前表格中已找不到以下字段，引用它们的材料或条件不会正确渲染：</p>
          <ul class="invalid-field-list">
            <li v-for="field in missingFieldNames" :key="field">{{ field }}</li>
          </ul>
          <p class="mt-2">请在表格中恢复这些列，或改用现有字段重新放置材料。</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="invalidFieldsDialog = false">知道了</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="excelErrorDialog" max-width="440">
      <v-card>
        <v-card-item>
          <div class="d-flex align-center">
            <v-icon color="error" size="28" class="mr-3">mdi-alert-circle</v-icon>
            <v-card-title class="pa-0">解析失败</v-card-title>
          </div>
        </v-card-item>
        <v-card-text>
          <p class="text-body-2">{{ excelErrorMessage }}</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="excelErrorDialog = false">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 文本预设编辑窗口 -->
    <v-dialog v-model="textDialogOpen" max-width="430">
      <v-card class="text-dialog-card" rounded="xl" elevation="8">
        <v-card-item class="text-dialog-header">
          <v-icon color="#be185d" size="20" class="mr-2">mdi-format-text</v-icon>
          <v-card-title class="text-dialog-title">{{ editingPresetId ? '编辑文本预设' : '添加文本预设' }}</v-card-title>
        </v-card-item>

        <v-card-text class="text-dialog-body">
          <v-textarea
            v-model="textForm.text"
            density="compact"
            variant="outlined"
            hide-details
            placeholder="输入自定义文本"
            rows="2"
            auto-grow
            class="text-dialog-textarea"
          />

          <div class="text-dialog-row">
            <v-icon size="16" color="#94a3b8">mdi-format-font</v-icon>
            <v-select
              v-model="textForm.fontFamily"
              :items="fontOptions"
              item-title="name"
              item-value="value"
              density="compact"
              variant="outlined"
              hide-details
              class="text-dialog-select"
            />
          </div>

          <div class="text-dialog-row">
            <v-icon size="16" color="#94a3b8">mdi-format-bold</v-icon>
            <v-btn-toggle
              v-model="textForm.fontWeight"
              mandatory
              density="compact"
              variant="outlined"
              divided
              class="text-weight-toggle"
            >
              <v-btn :value="400" size="x-small">常规</v-btn>
              <v-btn :value="700" size="x-small">粗体</v-btn>
            </v-btn-toggle>
            <v-icon size="16" color="#94a3b8" class="ml-3">mdi-arrow-expand-all</v-icon>
            <v-text-field
              v-model.number="textForm.size"
              type="number"
              density="compact"
              variant="outlined"
              hide-details
              :min="20"
              :max="400"
              class="text-size-field"
            />
          </div>

          <div class="text-dialog-row">
            <v-icon size="16" color="#94a3b8">mdi-opacity</v-icon>
            <v-slider
              v-model="textForm.opacity"
              density="compact"
              hide-details
              :min="0.1"
              :max="1"
              :step="0.05"
              thumb-size="16"
              track-size="3"
              color="#be185d"
              class="text-dialog-slider"
            />
          </div>

          <div class="text-dialog-row">
            <v-icon size="16" color="#94a3b8">mdi-palette</v-icon>
            <v-menu v-model="textColorMenu" :close-on-content-click="false" offset="8">
              <template #activator="{ props: menuProps }">
                <div class="text-color-swatch" :style="{ background: textForm.color }" v-bind="menuProps"></div>
              </template>
              <v-color-picker
                v-model="textForm.color"
                mode="hex"
                hide-inputs
                @update:model-value="textColorMenu = false"
              />
            </v-menu>
            <span class="text-color-hex">{{ textForm.color }}</span>
          </div>

          <div class="text-preview-box">
            <span class="text-preview-label">预览</span>
            <span class="text-preview-value" :style="presetPreviewStyle(textForm)">
              {{ textForm.text || '预览文字' }}
            </span>
          </div>
        </v-card-text>

        <v-card-actions class="text-dialog-actions">
          <v-spacer></v-spacer>
          <v-btn variant="text" rounded="lg" @click="textDialogOpen = false">取消</v-btn>
          <v-btn
            variant="flat"
            rounded="lg"
            color="#be185d"
            :disabled="!textForm.text.trim()"
            @click="saveTextPreset"
          >{{ editingPresetId ? '保存修改' : '保存预设' }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 签字 / 印章图片添加：隐藏文件选择器 -->
    <input
      ref="imageFileInput"
      type="file"
      accept=".png,.jpg,.jpeg,.webp,.bmp"
      class="hidden-file-input"
      @change="handleImageSelect"
    />

    <!-- 签字 / 印章图片处理：去底色 + 自动裁切 + 透明 PNG -->
    <ImageProcessDialog
      v-model="imageProcessDialog"
      :file="pendingImage?.file ?? null"
      :kind="pendingImage?.kind ?? 'signature'"
      :saving="savingImage"
      @confirm="confirmProcessedImage"
    />

    <!-- 签字 / 印章图片右键删除菜单 -->
    <div
      v-if="imageContextMenu.show"
      class="img-ctx-menu"
      :style="{ left: imageContextMenu.x + 'px', top: imageContextMenu.y + 'px' }"
      @click.stop
    >
      <button type="button" class="img-ctx-item" @click="deleteImage">
        <v-icon size="16" color="error">mdi-delete-outline</v-icon>
        <span>删除图片</span>
      </button>
    </div>
    <div
      v-if="imageContextMenu.show"
      class="img-ctx-backdrop"
      @click="closeImageContextMenu"
      @contextmenu.prevent="closeImageContextMenu"
    ></div>

    <!-- 循环块配置对话框 -->
    <v-dialog v-model="loopBlockDialog" max-width="640" persistent>
      <v-card rounded="xl" elevation="8">
        <v-card-item>
          <div class="d-flex align-center">
            <v-icon color="primary" size="24" class="mr-2">mdi-repeat</v-icon>
            <v-card-title class="pa-0">配置循环块</v-card-title>
          </div>
          <v-card-subtitle class="pa-0 mt-1">
            {{ currentLoopBlock?.anchorId }} · {{ currentLoopBlock?.loopType === 'tableRow' ? '表格行循环' : '段落循环' }}
          </v-card-subtitle>
        </v-card-item>

        <v-card-text class="pt-4">
          <v-row dense>
            <v-col cols="6">
              <v-text-field
                v-model="loopBlockForm.loopVar"
                label="循环变量名"
                density="compact"
                variant="outlined"
                hide-details
                placeholder="item"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model="loopBlockForm.listVar"
                label="列表变量名"
                density="compact"
                variant="outlined"
                hide-details
                placeholder="明细"
              />
            </v-col>
          </v-row>

          <v-row dense class="mt-2">
            <v-col cols="6">
              <v-select
                v-model="loopBlockForm.dataRange"
                :items="[{ title: '全部行', value: 'all' }, { title: '指定列非空的行', value: 'columnNonEmpty' }]"
                label="数据范围"
                density="compact"
                variant="outlined"
                hide-details
              />
            </v-col>
            <v-col cols="6">
              <v-select
                v-model="loopBlockForm.rangeColumn"
                :items="bpStore.fieldNames"
                label="范围列"
                density="compact"
                variant="outlined"
                hide-details
                :disabled="loopBlockForm.dataRange !== 'columnNonEmpty'"
                clearable
              />
            </v-col>
          </v-row>

          <div class="mt-4">
            <div class="d-flex align-center justify-space-between mb-2">
              <span class="text-subtitle-2">过滤条件</span>
              <v-btn size="small" variant="tonal" color="primary" @click="addLoopCondition">
                <v-icon size="16" class="mr-1">mdi-plus</v-icon>添加条件
              </v-btn>
            </div>

            <div v-for="(cond, idx) in loopBlockForm.conditions" :key="cond.id" class="d-flex align-center ga-2 mb-2">
              <v-select
                v-model="cond.field"
                :items="bpStore.fieldNames"
                density="compact"
                variant="outlined"
                hide-details
                placeholder="字段"
                style="width: 140px"
              />
              <v-select
                v-model="cond.op"
                :items="['等于', '不等于', '包含', '不包含', '为空', '不为空']"
                density="compact"
                variant="outlined"
                hide-details
                style="width: 100px"
              />
              <v-text-field
                v-model="cond.value"
                density="compact"
                variant="outlined"
                hide-details
                placeholder="值 或 {{当前行.字段名}}"
                class="flex-1"
              />
              <v-btn icon size="x-small" variant="text" color="error" @click="removeLoopCondition(idx)">
                <v-icon size="16">mdi-close</v-icon>
              </v-btn>
            </div>

            <v-radio-group v-model="loopBlockForm.matchMode" inline density="compact" hide-details class="mt-1">
              <v-radio label="满足所有条件" value="所有" />
              <v-radio label="满足任一条件" value="任一" />
            </v-radio-group>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-btn variant="text" color="error" @click="deleteLoopBlock">删除循环块</v-btn>
          <v-spacer />
          <v-btn variant="text" @click="loopBlockDialog = false">取消</v-btn>
          <v-btn color="primary" @click="saveLoopBlock">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 保存工作进度 -->
    <v-dialog v-model="saveDialog" max-width="460">
      <v-card rounded="xl" elevation="8">
        <v-card-item>
          <div class="d-flex align-center">
            <v-icon color="primary" size="24" class="mr-2">mdi-content-save-outline</v-icon>
            <v-card-title class="pa-0">保存工作进度</v-card-title>
          </div>
          <v-card-subtitle class="pa-0 mt-1">
            {{ bpStore.currentProjectId
              ? '将作为新版本保存到当前项目，之前的进度会保留在项目历史中'
              : '首次保存会创建一个项目，之后再次保存都会追加到同一个项目' }}
          </v-card-subtitle>
        </v-card-item>

        <v-card-text class="pt-4">
          <v-text-field
            v-model="saveTitle"
            label="记录名称"
            density="compact"
            variant="outlined"
            hide-details
            autofocus
            @keyup.enter="persistProgress()"
          />

          <div class="save-summary mt-3">
            <div class="save-summary-row">
              <v-icon size="14">mdi-file-document-outline</v-icon>
              <span>{{ templateFileName || '未选择模板' }}</span>
            </div>
            <div class="save-summary-row">
              <v-icon size="14">mdi-file-excel</v-icon>
              <span>{{ excelFileName || '未选择表格' }}</span>
            </div>
            <div v-if="bpStore.templateType === 'pdf'" class="save-summary-row">
              <v-icon size="14">mdi-tag-multiple-outline</v-icon>
              <span>{{ bpStore.iconList.length }} 个标注</span>
            </div>
            <div v-else class="save-summary-row">
              <v-icon size="14">mdi-repeat</v-icon>
              <span>{{ bpStore.loopBlocks.length }} 个循环块</span>
            </div>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-btn variant="text" rounded="lg" :disabled="savingProgress" @click="persistProgress({ exportAfter: true })">
            <v-icon start size="16">mdi-download-outline</v-icon>
            导出 JSON
          </v-btn>
          <v-spacer />
          <v-btn variant="text" rounded="lg" :disabled="savingProgress" @click="saveDialog = false">取消</v-btn>
          <v-btn
            variant="flat"
            rounded="lg"
            color="primary"
            :loading="savingProgress"
            :disabled="savingProgress"
            @click="persistProgress()"
          >保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 当前项目的历史版本 -->
    <WorkspaceHistoryDialog
      v-model="historyDialog"
      :data-path="bpStore.dataPath"
      :project-id="bpStore.currentProjectId"
      :project-title="bpStore.currentProjectTitle"
      :restoring-key="restoringRevisionKey"
      @restore="restoreRevision"
    />

    <v-snackbar v-model="progressSnackbar" :timeout="3200" location="bottom" rounded="lg">
      {{ progressMessage }}
      <template #actions>
        <v-btn v-if="hasProjectHistory" variant="text" size="small" @click="openProjectHistoryFromSnackbar">项目历史</v-btn>
        <v-btn variant="text" size="small" @click="goHistory">全部记录</v-btn>
        <v-btn variant="text" size="small" @click="progressSnackbar = false">关闭</v-btn>
      </template>
    </v-snackbar>

    <!-- 重置 / 清空标注等破坏性操作的确认框 -->
    <v-dialog
      :model-value="confirmKind !== null"
      max-width="420"
      @update:model-value="onConfirmDialogToggle"
    >
      <v-card v-if="confirmConfig" rounded="xl" elevation="8">
        <v-card-item>
          <div class="d-flex align-center">
            <v-icon color="error" size="22" class="mr-2">mdi-alert-circle-outline</v-icon>
            <v-card-title class="pa-0 confirm-title">{{ confirmConfig.title }}</v-card-title>
          </div>
        </v-card-item>
        <v-card-text class="confirm-text">{{ confirmConfig.message }}</v-card-text>
        <v-card-actions class="px-4 pb-3">
          <v-spacer />
          <v-btn variant="text" rounded="lg" @click="confirmKind = null">取消</v-btn>
          <v-btn color="error" variant="flat" rounded="lg" @click="confirmAction">
            {{ confirmConfig.confirmText }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { useRouter } from 'vue-router'
import { invoke, convertFileSrc } from '@tauri-apps/api/core'
import { readDir, exists, writeFile, mkdir, remove, stat } from '@tauri-apps/plugin-fs'
import { open as openFileDialog } from '@tauri-apps/plugin-dialog'
import { Store } from '@tauri-apps/plugin-store'
import PdfViewer from '@/components/pdfview/PdfViewer.vue'
import DocxViewer from '@/components/docxview/DocxViewer.vue'
import WorkspaceHistoryDialog from '@/components/WorkspaceHistoryDialog.vue'
import ImageProcessDialog from '@/components/ImageProcessDialog.vue'
import { useBPStore } from '@/stores/bpstore'
import type { IconOption, LoopBlock, Condition } from '@/types/icon'
import type { ImageProcessKind } from '@/utils/imageProcess'
import type { NamePart, WorkspaceSnapshot } from '@/types/workspace'
import {
  exportWorkspaceJson,
  listWorkspaceRevisions,
  readPathAsFile,
  revisionKey,
  saveWorkspace,
} from '@/utils/workspace'
import { getFontsList, loadCustomFonts } from '@/utils/fontLoader'

const pdfSrc = ref<string>('')
const bpStore = useBPStore()
const router = useRouter()
const docxViewerRef = ref<InstanceType<typeof DocxViewer> | null>(null)

const activeMaterialNav = ref('table')
const materialNavItems = computed(() => {
  const items = [
    { title: '表格', value: 'table', icon: 'mdi-table' },
    { title: '签字', value: 'signature', icon: 'mdi-draw-pen' },
    { title: '印章', value: 'seal', icon: 'mdi-seal-variant' },
    { title: '图标', value: 'icon', icon: 'mdi-shape-outline' },
  ]
  // DOCX 模板不提供文本材料
  if (bpStore.templateType !== 'docx') {
    items.push({ title: '文本', value: 'text', icon: 'mdi-format-text' })
  }
  return items
})

// 切换到 DOCX 后若停留在“文本”板块，回退到“表格”
watch(() => bpStore.templateType, (type) => {
  if (type === 'docx' && activeMaterialNav.value === 'text') {
    activeMaterialNav.value = 'table'
  }
})

// 鼠标停留切换材料板块（带短暂延迟，避免滑过时闪烁）
let navHoverTimer: ReturnType<typeof setTimeout> | null = null
function setActiveNav(value: string) {
  if (navHoverTimer) clearTimeout(navHoverTimer)
  navHoverTimer = setTimeout(() => {
    activeMaterialNav.value = value
  }, 80)
}
function clearHoverTimer() {
  if (navHoverTimer) {
    clearTimeout(navHoverTimer)
    navHoverTimer = null
  }
}

function startFieldDrag(event: DragEvent, fieldName: string) {
  if (!event.dataTransfer) return
  const option: IconOption = {
    type: 'field',
    fieldName,
    fontFamily: '楷体',
    size: 120,
  }
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/x-batchprint-option', JSON.stringify({ option, panel: 'table' }))
}

const iconGroups = [
  { value: 'marks', label: '复选框', icons: [
    { char: '☐', label: '空方框' }, { char: '☑', label: '勾选方框' },
    { char: '☒', label: '叉选方框' }, { char: '✓', label: '对勾' },
    { char: '✗', label: '叉号' }, { char: '✔', label: '粗对勾' },
    { char: '✘', label: '粗叉号' }, { char: '●', label: '实心圆' },
  ]},
  { value: 'stars', label: '星形', icons: [
    { char: '★', label: '实心星' }, { char: '☆', label: '空心星' },
    { char: '✦', label: '四角星' }, { char: '✧', label: '空心四角' },
    { char: '◆', label: '实心菱形' }, { char: '◇', label: '空心菱形' },
    { char: '■', label: '实心方块' }, { char: '□', label: '空心方块' },
  ]},
  { value: 'arrows', label: '箭头', icons: [
    { char: '→', label: '右箭头' }, { char: '←', label: '左箭头' },
    { char: '↑', label: '上箭头' }, { char: '↓', label: '下箭头' },
    { char: '↔', label: '左右箭头' }, { char: '↕', label: '上下箭头' },
    { char: '▶', label: '右三角' }, { char: '◀', label: '左三角' },
  ]},
  { value: 'shapes', label: '图形', icons: [
    { char: '▲', label: '实心三角' }, { char: '△', label: '空心三角' },
    { char: '▼', label: '倒三角' }, { char: '▽', label: '空心倒三角' },
    { char: '○', label: '空心圆' }, { char: '♥', label: '红心' },
    { char: '♦', label: '方块' }, { char: '♣', label: '梅花' },
  ]},
  { value: 'office', label: '办公', icons: [
    { char: '☎', label: '电话' }, { char: '✉', label: '信封' },
    { char: '✎', label: '铅笔' }, { char: '⌂', label: '房子' },
    { char: '⌘', label: '命令键' }, { char: '⏎', label: '回车' },
    { char: '⌫', label: '退格' }, { char: '☺', label: '笑脸' },
  ]},
  { value: 'info', label: '提示', icons: [
    { char: '⚡', label: '闪电' }, { char: '⚠', label: '警告' },
    { char: 'ℹ', label: '信息' }, { char: '©', label: '版权' },
    { char: '®', label: '注册商标' }, { char: '™', label: '商标' },
    { char: '♻', label: '回收' }, { char: '☹', label: '哭脸' },
  ]},
]

function startImageDrag(event: DragEvent, type: 'signature' | 'seal', index: number) {
  if (!event.dataTransfer) return
  const list = type === 'signature' ? bpStore.imageList_signature : bpStore.imageList_seal
  const option: IconOption = { type: 'image', imageKind: type, src: list[index] ?? '', size: 120 }
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/x-batchprint-option', JSON.stringify({ option, panel: type }))
}

function startIconDrag(event: DragEvent, char: string) {
  if (!event.dataTransfer) return
  const option: IconOption = {
    type: 'icon', icon: char, color: '#000000', opacity: 1, size: 120,
  }
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/x-batchprint-option', JSON.stringify({ option, panel: 'icon' }))
}

/* ========= 文本预设 ========= */
interface TextPreset {
  id: string
  text: string
  fontFamily: string
  fontWeight: number
  color: string
  opacity: number
  size: number
}

interface FontOption {
  name: string
  value: string
  type: 'system' | 'custom'
  file?: string
  url?: string
}

const textPresets = ref<TextPreset[]>([])
const textDialogOpen = ref(false)
const textColorMenu = ref(false)
const fontOptions = ref<FontOption[]>([])
/** 正在编辑的预设 id；为空表示「新增」模式 */
const editingPresetId = ref<string | null>(null)
/** 拖拽刚结束时浏览器可能补发一次 click，用时间戳短暂屏蔽，避免误开编辑窗口 */
let suppressPresetClickUntil = 0

function createEmptyTextForm(): TextPreset {
  return {
    id: '',
    text: '',
    fontFamily: fontOptions.value[0]?.value ?? '楷体',
    fontWeight: 400,
    color: '#000000',
    opacity: 1,
    size: 120,
  }
}

const textForm = ref<TextPreset>(createEmptyTextForm())

let textPresetStore: Store | null = null

function genPresetId(): string {
  return `tp_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

/** 打开文本弹窗：传入 preset 为编辑已有预设，缺省为新增 */
function openTextDialog(preset?: TextPreset) {
  editingPresetId.value = preset ? preset.id : null
  textForm.value = preset ? { ...preset } : createEmptyTextForm()
  textColorMenu.value = false
  textDialogOpen.value = true
}

/** 拖拽结束后短暂屏蔽随后的 click，避免「拖出去」被当成「点击编辑」 */
function handlePresetDragEnd() {
  suppressPresetClickUntil = Date.now() + 200
}

/** 点击预设 chip：打开编辑窗口 */
function openPresetEditor(preset: TextPreset) {
  if (Date.now() < suppressPresetClickUntil) return
  openTextDialog(preset)
}

async function saveTextPreset() {
  const text = textForm.value.text.trim()
  if (!text) return
  const editingId = editingPresetId.value
  const index = editingId ? textPresets.value.findIndex(p => p.id === editingId) : -1
  if (index >= 0) {
    textPresets.value.splice(index, 1, { ...textForm.value, id: editingId as string, text })
  } else {
    textPresets.value.push({ ...textForm.value, id: genPresetId(), text })
  }
  await persistTextPresets()
  textDialogOpen.value = false
  editingPresetId.value = null
}

async function deleteTextPreset(id: string) {
  textPresets.value = textPresets.value.filter(p => p.id !== id)
  await persistTextPresets()
}

async function loadTextPresets() {
  try {
    textPresetStore = await Store.load('text_presets.json')
    const saved = await textPresetStore.get<TextPreset[]>('presets')
    textPresets.value = Array.isArray(saved) ? saved : []
  } catch (error) {
    console.error('加载文本预设失败:', error)
    textPresets.value = []
  }
}

async function persistTextPresets() {
  try {
    if (!textPresetStore) {
      textPresetStore = await Store.load('text_presets.json')
    }
    await textPresetStore.set('presets', textPresets.value)
    await textPresetStore.save()
  } catch (error) {
    console.error('保存文本预设失败:', error)
  }
}

function presetPreviewStyle(preset: TextPreset) {
  return {
    fontFamily: preset.fontFamily,
    fontWeight: preset.fontWeight,
    color: preset.color,
    opacity: preset.opacity,
    fontSize: `${Math.max(10, Math.min(preset.size * 0.12, 18))}px`,
  }
}

function startPresetTextDrag(event: DragEvent, preset: TextPreset) {
  if (!event.dataTransfer) return
  const option: IconOption = {
    type: 'text',
    text: preset.text,
    fontFamily: preset.fontFamily,
    fontWeight: preset.fontWeight,
    color: preset.color,
    opacity: preset.opacity,
    size: preset.size,
  }
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/x-batchprint-option', JSON.stringify({ option, panel: 'text' }))
}

/* ========= 字体列表（文本预设弹窗用） ========= */
async function loadFonts() {
  try {
    await loadCustomFonts(bpStore.dataPath)
    fontOptions.value = await getFontsList(bpStore.dataPath)
  } catch (error) {
    console.error('加载字体列表失败:', error)
    fontOptions.value = [
      { name: '楷体', value: '楷体', type: 'system' },
      { name: '微软雅黑', value: '微软雅黑', type: 'system' },
      { name: '宋体', value: '宋体', type: 'system' },
      { name: '黑体', value: '黑体', type: 'system' },
      { name: 'Arial', value: 'Arial', type: 'system' },
    ]
  }
}

/* ========= 设置路径下的签字 / 印章图片 ========= */
const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']

async function loadImagesFromDir(dirPath: string): Promise<string[]> {
  try {
    if (!await exists(dirPath)) return []
    const files = await readDir(dirPath)
    return files
      .filter(file => file.isFile)
      .map(file => file.name)
      .filter(name => imageExtensions.some(ext => name.toLowerCase().endsWith(ext)))
      .map(name => convertFileSrc(`${dirPath}/${name}`))
  } catch (error) {
    console.error(`读取图片目录失败 ${dirPath}:`, error)
    return []
  }
}

async function refreshImageLists() {
  if (!bpStore.dataPath) return
  const [sig, seal] = await Promise.all([
    loadImagesFromDir(`${bpStore.dataPath}/signImg`),
    loadImagesFromDir(`${bpStore.dataPath}/sealImg`),
  ])
  bpStore.imageList_signature = sig
  bpStore.imageList_seal = seal
}

/* ========= 添加签字 / 印章图片 ========= */
const imagePickerKind = ref<'signature' | 'seal'>('signature')
const imageFileInput = ref<HTMLInputElement | null>(null)
/** 待处理的上传文件：选图后先进入处理对话框，确认后才写入磁盘 */
const pendingImage = ref<{ file: File; kind: ImageProcessKind } | null>(null)
const imageProcessDialog = ref(false)
const savingImage = ref(false)

function triggerImagePicker(kind: 'signature' | 'seal') {
  if (!bpStore.dataPath) return
  imagePickerKind.value = kind
  imageFileInput.value?.click()
}

function handleImageSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  // 先清空 input，保证连续选择同一张图片时也能触发 change
  input.value = ''
  if (!file) return
  if (!bpStore.dataPath) {
    alert('请先设置数据目录')
    return
  }
  pendingImage.value = { file, kind: imagePickerKind.value }
  imageProcessDialog.value = true
}

function timestampStamp(date: Date): string {
  const pad = (n: number, len = 2) => String(n).padStart(len, '0')
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
    '-',
    pad(date.getHours()),
    pad(date.getMinutes()),
    pad(date.getSeconds()),
    '-',
    pad(date.getMilliseconds(), 3),
  ].join('')
}

async function confirmProcessedImage(payload: { blob: Blob; ext: string; original: boolean }) {
  const pending = pendingImage.value
  if (!pending || !bpStore.dataPath || savingImage.value) return
  const subDir = pending.kind === 'signature' ? 'signImg' : 'sealImg'
  const dirPath = `${bpStore.dataPath}/${subDir}`
  // 原图单独归档，避免被图片列表扫描到（readDir 只取顶层文件）
  const originalDir = `${dirPath}/.originals`
  savingImage.value = true
  try {
    if (!await exists(dirPath)) {
      await mkdir(dirPath, { recursive: true })
    }
    // 文件名全 ASCII + 时间戳：避免同名覆盖导致图片缓存命中旧图
    const base = pending.kind === 'signature' ? 'sig' : 'seal'
    const fileName = `${base}-${timestampStamp(new Date())}.${payload.ext}`
    if (!payload.original) {
      if (!await exists(originalDir)) {
        await mkdir(originalDir, { recursive: true })
      }
      const originalBuf = await pending.file.arrayBuffer()
      await writeFile(`${originalDir}/${fileName}`, new Uint8Array(originalBuf))
    }
    const buf = await payload.blob.arrayBuffer()
    await writeFile(`${dirPath}/${fileName}`, new Uint8Array(buf))
    await refreshImageLists()
    imageProcessDialog.value = false
  } catch (error) {
    console.error('添加图片失败:', error)
    alert('添加图片失败，请检查路径权限')
  } finally {
    savingImage.value = false
  }
}

/* ========= 右键删除签字 / 印章图片 ========= */
const imageContextMenu = ref({
  show: false,
  x: 0,
  y: 0,
  kind: 'signature' as 'signature' | 'seal',
  index: -1,
})

function onImageContextMenu(event: MouseEvent, kind: 'signature' | 'seal', index: number) {
  event.preventDefault()
  imageContextMenu.value = {
    show: true,
    x: event.clientX,
    y: event.clientY,
    kind,
    index,
  }
}

function closeImageContextMenu() {
  imageContextMenu.value.show = false
}

async function deleteImage() {
  const { kind, index } = imageContextMenu.value
  closeImageContextMenu()
  if (index < 0 || !bpStore.dataPath) return
  const list = kind === 'signature' ? bpStore.imageList_signature : bpStore.imageList_seal
  const src = list[index]
  if (!src) return
  const subDir = kind === 'signature' ? 'signImg' : 'sealImg'
  // convertFileSrc 生成 URL 时会编码路径，先整体解码再取最后一段文件名
  const decoded = decodeURIComponent(src)
  const fileName = decoded.split(/[/\\]/).pop() || ''
  if (!fileName) return
  const filePath = `${bpStore.dataPath}/${subDir}/${fileName}`
  try {
    await remove(filePath)
    await refreshImageLists()
  } catch (error) {
    console.error('删除图片失败:', error)
    alert('删除图片失败，请检查文件是否被占用')
  }
}

const mergedCellsDialog = ref(false)
const excelErrorDialog = ref(false)
const excelErrorMessage = ref('')
const invalidFieldsDialog = ref(false)
const missingFieldNames = ref<string[]>([])

/** 模板 / 表格文件的最后修改时间（毫秒），用于提示磁盘文件是否已被外部改动 */
const templateMtime = ref<number | null>(null)
const excelMtime = ref<number | null>(null)
const reloading = ref(false)

const generating = ref(false)
const generateProgress = ref(0)
const generateCurrent = ref(0)
const generateTotal = ref(0)
const resultDialog = ref(false)
const resultSuccess = ref(false)
const resultMessage = ref('')
const resultPath = ref('')

/* ========= 循环块配置 ========= */
const loopBlockDialog = ref(false)
const currentLoopBlock = ref<LoopBlock | null>(null)
const pendingAnchorId = ref('')
const pendingLoopType = ref<'paragraph' | 'tableRow'>('paragraph')
const loopBlockForm = ref({
  loopVar: 'item',
  listVar: '明细',
  dataRange: 'all' as 'all' | 'columnNonEmpty',
  rangeColumn: '' as string | undefined,
  conditions: [] as Condition[],
  matchMode: '所有' as '所有' | '任一',
})

const nameParts = ref<NamePart[]>([])
const addMenuOpen = ref(false)
const customText = ref('')
const insertIndex = ref(0)
const nameInputRef = ref<HTMLElement | null>(null)

const setInsert = (index: number) => {
  insertIndex.value = Math.max(0, Math.min(index, nameParts.value.length))
  nameInputRef.value?.focus()
}

const insertPart = (part: NamePart) => {
  const idx = Math.max(0, Math.min(insertIndex.value, nameParts.value.length))
  nameParts.value.splice(idx, 0, part)
  insertIndex.value = idx + 1
  addMenuOpen.value = false
  nameInputRef.value?.focus()
}

const partIcons: Partial<Record<NamePart['type'], string>> = {
  field: 'mdi-table-column',
  seq: 'mdi-numeric',
}

const partColors: Record<NamePart['type'], string> = {
  field: 'primary',
  seq: 'teal',
  text: 'orange',
  sep: 'grey',
}

const seqOptions = [
  { title: '1, 2, 3 …', digits: 0 },
  { title: '01, 02, 03 …', digits: 2 },
  { title: '001, 002, 003 …', digits: 3 },
  { title: '0001, 0002, 0003 …', digits: 4 },
]

const sepOptions = [
  { title: '下划线 _', value: '_' },
  { title: '连字符 -', value: '-' },
  { title: '点 .', value: '.' },
  { title: '空格', value: ' ' },
]

const partLabel = (part: NamePart): string => {
  if (part.type === 'field') return part.field || ''
  if (part.type === 'seq') {
    return part.digits ? `${'1'.padStart(part.digits, '0')}…` : '1,2,3…'
  }
  if (part.type === 'sep') return part.text === ' ' ? '空格' : part.text || ''
  return part.text || ''
}

const addFieldPart = (fieldName: string) => {
  insertPart({ type: 'field', field: fieldName })
}

const addSeqPart = (digits: number) => {
  insertPart({ type: 'seq', start: 1, digits })
}

const addTextPart = () => {
  if (!customText.value) return
  insertPart({ type: 'text', text: customText.value })
  customText.value = ''
}

const addSepPart = (value: string) => {
  insertPart({ type: 'sep', text: value })
}

const normalizeSeps = () => {
  const parts = nameParts.value
  for (let i = parts.length - 1; i >= 0; i--) {
    if (parts[i].type !== 'sep') continue
    if (i === 0 || i === parts.length - 1 || parts[i - 1].type === 'sep') {
      parts.splice(i, 1)
      if (insertIndex.value > i) {
        insertIndex.value--
      }
    }
  }
}

const removeNamePart = (index: number) => {
  const parts = nameParts.value
  parts.splice(index, 1)
  if (insertIndex.value > index) {
    insertIndex.value--
  }
  nameInputRef.value?.focus()
}

const handleNameKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Backspace') {
    if (insertIndex.value > 0) {
      removeNamePart(insertIndex.value - 1)
    }
    e.preventDefault()
  } else if (e.key === 'Delete') {
    if (insertIndex.value < nameParts.value.length) {
      removeNamePart(insertIndex.value)
    }
    e.preventDefault()
  } else if (e.key === 'ArrowLeft') {
    setInsert(insertIndex.value - 1)
    e.preventDefault()
  } else if (e.key === 'ArrowRight') {
    setInsert(insertIndex.value + 1)
    e.preventDefault()
  }
}

const buildFileName = (rowIndex: number): string => {
  const row = bpStore.excelContent[rowIndex] || []
  return nameParts.value
    .map(part => {
      if (part.type === 'field') {
        const idx = bpStore.fieldNames.indexOf(part.field || '')
        const val = idx >= 0 ? row[idx] : undefined
        return val === null || val === undefined ? (part.field ? `{${part.field}}` : '') : String(val)
      }
      if (part.type === 'seq') {
        const num = (part.start ?? 1) + rowIndex
        return part.digits ? String(num).padStart(part.digits, '0') : String(num)
      }
      return part.text || ''
    })
    .join('')
}

const fileNamePreview = computed(() => {
  const name = buildFileName(0)
  const ext = bpStore.templateType === 'pdf' ? '.pdf' : '.docx'
  return (name || '1') + ext
})

async function apiPost(url: string, formData: FormData, retries = 30): Promise<any> {
  for (let i = 0; i < retries; i++) {
    try {
      return await axios.post(url, formData)
    } catch {
      if (i < retries - 1) {
        await new Promise(r => setTimeout(r, 1000))
      } else {
        throw new Error(`无法连接后端服务: ${url}`)
      }
    }
  }
}

onMounted(async () => {
  if (bpStore.pdfSrc) {
    pdfSrc.value = bpStore.pdfSrc
  }
  await Promise.all([
    loadFonts(),
    loadTextPresets(),
    refreshImageLists(),
    bpStore.loadMaterialStyles(),
  ])
  // 首次进入本页时也可能带着历史记录（例如从 /history 直达）
  await applyPendingRestore()
})

// 本页被 keep-alive 缓存：从历史记录页返回时走 onActivated，
// 此时 DOM 已重新挂载，恢复后 PdfViewer 才能正常渲染
onActivated(async () => {
  await applyPendingRestore()
})

watch(() => bpStore.dataPath, async (newPath) => {
  if (!newPath) return
  await Promise.all([
    loadFonts(),
    refreshImageLists(),
  ])
})

watch(() => bpStore.fontsVersion, () => {
  loadFonts()
})

/* ========= 模板 / 表格：以路径为唯一持久化引用 ========= */

/**
 * 最近一次由编辑器 `save()` 写回磁盘的 DOCX 字节。
 * 只在「保存工作进度」回写成功后更新，因此它一定是编辑器自身的序列化结果——
 * 用它做基线比较不会因为「重新序列化的字节差异」误报未保存改动。
 * 为空表示本次会话还没有回写过（无法判断），此时生成不做提示。
 */
let docxDiskBytes: Uint8Array | null = null

/** 取路径最后一段作为展示文件名 */
function basename(path: string): string {
  return path ? path.split(/[/\\]/).pop() || path : ''
}

/** 释放不再使用的 blob URL，避免预览切换时内存泄漏 */
function releaseObjectUrl(url: string) {
  if (url && url.startsWith('blob:')) URL.revokeObjectURL(url)
}

/** 读取文件最后修改时间（毫秒）；读不到时返回 null */
async function readMtime(path: string): Promise<number | null> {
  if (!path) return null
  try {
    const info = await stat(path)
    return info.mtime ? info.mtime.getTime() : null
  } catch {
    return null
  }
}

function formatMtime(mtime: number | null): string {
  if (!mtime) return '修改时间：未知'
  const d = new Date(mtime)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `修改时间：${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 当前模板（PDF / DOCX）的原始文件路径 */
const templatePath = computed(() => (bpStore.templateType === 'pdf' ? bpStore.pdfPath : bpStore.docxPath))
const excelPath = computed(() => bpStore.excelPath)
const templateFileName = computed(() => basename(templatePath.value))
const excelFileName = computed(() => basename(bpStore.excelPath))
const hasTemplate = computed(() => !!templatePath.value)
const hasAnyPath = computed(() => !!templatePath.value || !!bpStore.excelPath)
/** 项目存在历史版本（除当前版本外还有旧版本）时，才在预览区显示历史图标 */
const hasProjectHistory = computed(() => bpStore.currentProjectRevisionCount > 1)
const templateMtimeText = computed(() => formatMtime(templateMtime.value))
const excelMtimeText = computed(() => formatMtime(excelMtime.value))

/** 刷新当前项目的版本数量（用于决定是否显示历史图标） */
async function refreshProjectRevisionCount() {
  if (!bpStore.currentProjectId || !bpStore.dataPath) {
    bpStore.currentProjectRevisionCount = 0
    return
  }
  try {
    const revisions = await listWorkspaceRevisions(bpStore.dataPath, bpStore.currentProjectId)
    bpStore.currentProjectRevisionCount = revisions.length
  } catch (error) {
    console.warn('读取项目版本数量失败:', error)
    bpStore.currentProjectRevisionCount = 0
  }
}

async function refreshTemplateMtime() {
  templateMtime.value = await readMtime(templatePath.value)
}

async function refreshExcelMtime() {
  excelMtime.value = await readMtime(bpStore.excelPath)
}

async function pickTemplate() {
  try {
    const selected = await openFileDialog({
      multiple: false,
      directory: false,
      title: '选择模板（PDF / DOCX）',
      filters: [{ name: '模板文件', extensions: ['pdf', 'docx'] }],
    })
    if (!selected || Array.isArray(selected)) return
    // 换了不同的模板/表格文件，视为一份新的内容：解除当前项目关联，下次保存创建新项目
    const currentTemplate = bpStore.templateType === 'pdf' ? bpStore.pdfPath : bpStore.docxPath
    if (bpStore.currentProjectId && selected !== currentTemplate) bpStore.clearCurrentProject()
    await loadTemplateFromPath(selected)
  } catch (error) {
    console.error('选择模板失败:', error)
    notifyProgress(`选择模板失败：${(error as Error)?.message || '未知错误'}`)
  }
}

async function pickExcel() {
  try {
    const selected = await openFileDialog({
      multiple: false,
      directory: false,
      title: '选择 Excel 数据',
      filters: [{ name: 'Excel 数据', extensions: ['xlsx', 'xls'] }],
    })
    if (!selected || Array.isArray(selected)) return
    if (bpStore.currentProjectId && selected !== bpStore.excelPath) bpStore.clearCurrentProject()
    await loadExcelFromPath(selected)
    validateFieldReferences()
  } catch (error) {
    console.error('选择 Excel 失败:', error)
    notifyProgress(`选择 Excel 失败：${(error as Error)?.message || '未知错误'}`)
  }
}

/**
 * 按路径装载模板：识别类型、读取预览字节并解析 DOCX 结构。
 * 选择新模板时（默认）会清空标注，避免不同模板之间互相污染；
 * keepAnnotations=true 用于「重新加载」，保留当前标注。
 */
async function loadTemplateFromPath(path: string, options: { keepAnnotations?: boolean } = {}) {
  const file = await readPathAsFile(path)
  if (!file) {
    notifyProgress('模板文件不存在或无法读取')
    return
  }

  const lower = file.name.toLowerCase()
  const isPdf = lower.endsWith('.pdf')
  const isDocx = lower.endsWith('.docx')
  if (!isPdf && !isDocx) {
    alert('请选择有效的 PDF 或 DOCX 模板文件')
    return
  }

  const keep = options.keepAnnotations === true
  docxDiskBytes = null

  if (isPdf) {
    bpStore.templateType = 'pdf'
    if (!keep) {
      bpStore.iconList = []
      bpStore.loopBlocks = []
      bpStore.docxStructure = []
    }
    bpStore.docxFile = null
    bpStore.docxPath = ''
    releaseObjectUrl(pdfSrc.value)
    const url = URL.createObjectURL(file)
    pdfSrc.value = url
    bpStore.pdfSrc = url
    bpStore.pdfFile = file
    bpStore.pdfPath = path
  } else {
    bpStore.templateType = 'docx'
    if (!keep) bpStore.iconList = []
    bpStore.pdfFile = null
    bpStore.pdfPath = ''
    releaseObjectUrl(pdfSrc.value)
    pdfSrc.value = ''
    bpStore.pdfSrc = ''
    bpStore.docxFile = file
    bpStore.docxPath = path
    await parseDocxStructure(file)
  }

  // 换模板（不保留旧标注）视为全新的材料列表，保存按钮回到「暂无改动」
  if (!keep) savedProgressSignature.value = progressSignature()

  await refreshTemplateMtime()
}

/** 按路径装载 Excel 并重新解析字段；引用失效由 validateFieldReferences 统一校验 */
async function loadExcelFromPath(path: string) {
  const file = await readPathAsFile(path)
  if (!file) {
    notifyProgress('表格文件不存在或无法读取')
    return
  }

  const lower = file.name.toLowerCase()
  if (!lower.endsWith('.xlsx') && !lower.endsWith('.xls')) {
    alert('请选择有效的Excel文件')
    return
  }

  bpStore.excelFile = file
  bpStore.excelPath = path
  releaseObjectUrl(bpStore.excelSrc)
  bpStore.excelSrc = URL.createObjectURL(file)
  bpStore.fieldNames = []
  bpStore.excelContent = []

  const formData = new FormData()
  formData.append('file', file)
  try {
    const res = await apiPost('http://localhost:8000/get_excel_headers', formData)
    if (res.data.has_merged_cells) {
      mergedCellsDialog.value = true
    } else {
      bpStore.fieldNames = res.data.headers
      bpStore.excelContent = res.data.content
    }
  } catch (e: any) {
    excelErrorMessage.value = e.message || '无法解析 Excel 文件，请检查后端服务是否正常'
    excelErrorDialog.value = true
  }

  await refreshExcelMtime()
}

/**
 * Excel（重新）解析后校验各处引用的字段是否仍然存在：
 * - 文件名片段里失效的字段会被剔除（沿用原有行为）
 * - 材料 / 循环条件里引用的失效字段不静默保留，弹窗交由用户确认
 */
function validateFieldReferences() {
  if (bpStore.fieldNames.length === 0) return
  const present = new Set(bpStore.fieldNames)
  const missing = new Set<string>()
  const add = (field?: string | null) => {
    if (field && !present.has(field)) missing.add(field)
  }

  for (const icon of bpStore.iconList) {
    if (icon.option?.type === 'field') add(icon.option.fieldName)
    icon.conditions?.forEach(c => add(c.field))
    icon.groups?.forEach(g => g.conditions.forEach(c => add(c.field)))
  }
  for (const block of bpStore.loopBlocks) {
    block.conditions?.forEach(c => add(c.field))
  }

  nameParts.value = nameParts.value.filter(p => p.type !== 'field' || present.has(p.field || ''))
  insertIndex.value = Math.min(insertIndex.value, nameParts.value.length)
  normalizeSeps()

  missingFieldNames.value = [...missing]
  if (missingFieldNames.value.length > 0) invalidFieldsDialog.value = true
}

/** 按当前记录的路径重新读取模板与表格，用于原文件被外部改动后同步 */
async function reloadFromPaths() {
  const tplPath = templatePath.value
  if (!tplPath && !bpStore.excelPath) {
    notifyProgress('尚未选择模板或表格')
    return
  }

  if (bpStore.templateType === 'docx' && tplPath) {
    const ok = window.confirm('重新加载会用磁盘上的模板文件覆盖编辑器当前内容，未写回的改动将丢失。是否继续？')
    if (!ok) return
  }

  reloading.value = true
  try {
    if (tplPath) await loadTemplateFromPath(tplPath, { keepAnnotations: true })
    if (bpStore.excelPath) await loadExcelFromPath(bpStore.excelPath)
    validateFieldReferences()
    notifyProgress('已按磁盘文件重新加载')
  } catch (error) {
    console.error('重新加载失败:', error)
    notifyProgress(`重新加载失败：${(error as Error)?.message || '未知错误'}`)
  } finally {
    reloading.value = false
  }
}

const parseDocxStructure = async (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  try {
    const res = await apiPost('http://localhost:8000/api/docx/parse', formData)
    if (res.data.error) {
      alert(res.data.error)
      bpStore.docxStructure = []
      return
    }
    bpStore.docxStructure = res.data.structure || []
  } catch (e: any) {
    alert('解析 DOCX 失败: ' + (e.message || '未知错误'))
    bpStore.docxStructure = []
  }
}

const generateBatchPDF = async () => {
  if (!bpStore.excelFile) {
    resultSuccess.value = false
    resultMessage.value = '请先选择Excel数据文件'
    resultPath.value = ''
    resultDialog.value = true
    return
  }

  // DOCX 模板的字段/图片直接插入在文档内，不依赖 iconList；仅 PDF 模板要求先放置材料
  if (bpStore.templateType === 'pdf' && bpStore.iconList.length === 0) {
    resultSuccess.value = false
    resultMessage.value = '请先在模板上放置材料，图标列表为空'
    resultPath.value = ''
    resultDialog.value = true
    return
  }

  if (bpStore.templateType === 'pdf' && !bpStore.pdfFile) {
    resultSuccess.value = false
    resultMessage.value = '请先选择PDF模板'
    resultPath.value = ''
    resultDialog.value = true
    return
  }

  if (bpStore.templateType === 'docx' && !bpStore.docxFile) {
    resultSuccess.value = false
    resultMessage.value = '请先选择DOCX模板'
    resultPath.value = ''
    resultDialog.value = true
    return
  }

  generating.value = true
  generateProgress.value = 0
  generateCurrent.value = 0
  generateTotal.value = 0

  try {
    const formData = new FormData()
    formData.append('excel_file', bpStore.excelFile)
    formData.append('path', bpStore.dataPath || '')
    formData.append('icon_list', JSON.stringify(bpStore.iconList))
    formData.append('filename_config', JSON.stringify({ parts: nameParts.value, separator: '' }))

    let endpoint = ''
    if (bpStore.templateType === 'pdf') {
      formData.append('pdf_file', bpStore.pdfFile!)
      formData.append('pdf_scale', bpStore.pdfScale.toString())
      endpoint = 'http://localhost:8000/generate_batch_pdf'
    } else {
      // 上传编辑器内最新的 DOCX 内容（包含用户在文档中的自由编辑），保存失败时回退原文件
      const editedBuf: ArrayBuffer | null = await docxViewerRef.value?.getDocxArrayBuffer?.() ?? null
      const originalFile = bpStore.docxFile!
      // 编辑器内容与最近一次写回磁盘的内容不一致时，仅提示、不自动回写，
      // 让用户知道本次生成用的是编辑器内的最新内容。
      if (editedBuf && docxDiskBytes !== null && !bytesEqual(new Uint8Array(editedBuf), docxDiskBytes)) {
        const proceed = window.confirm('编辑器中有尚未写回模板原文件的改动，本次生成会使用编辑器内的最新内容（不会写回原文件）。是否继续？')
        if (!proceed) return
      }
      const uploadFile = editedBuf
        ? new File([editedBuf], originalFile.name, {
            type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          })
        : originalFile
      formData.append('docx_file', uploadFile)
      formData.append('loop_blocks', JSON.stringify(bpStore.loopBlocks))
      endpoint = 'http://localhost:8000/generate_batch_docx'
    }

    const resp = await fetch(endpoint, { method: 'POST', body: formData })
    if (!resp.ok || !resp.body) {
      throw new Error(`后端响应异常: HTTP ${resp.status}`)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let donePayload: { msg?: string; path?: string } | null = null

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() || ''
      for (const chunk of chunks) {
        const line = chunk.trim()
        if (!line.startsWith('data:')) continue
        const evt = JSON.parse(line.slice(5).trim())
        if (evt.type === 'start') {
          generateTotal.value = evt.total || 0
        } else if (evt.type === 'progress') {
          generateCurrent.value = evt.current
          generateTotal.value = evt.total
          generateProgress.value = evt.total ? (evt.current / evt.total) * 100 : 0
        } else if (evt.type === 'done') {
          donePayload = evt
        } else if (evt.type === 'error') {
          throw new Error(evt.message || '生成失败')
        }
      }
    }

    if (!donePayload) throw new Error('未收到后端完成事件')

    resultSuccess.value = true
    resultMessage.value = donePayload.msg || '批量生成成功！'
    resultPath.value = donePayload.path || ''
    resultDialog.value = true
  } catch (error) {
    console.error('生成失败:', error)
    resultSuccess.value = false
    resultMessage.value = (error as Error)?.message || '批量生成出错，请查看浏览器控制台'
    resultPath.value = ''
    resultDialog.value = true
  } finally {
    generating.value = false
  }
}

async function openFolder(path: string) {
  try {
    await invoke('open_folder', { path })
  } catch (e) {
    console.error('打开文件夹失败:', e)
  }
}

const handleReset = () => {
  releaseObjectUrl(pdfSrc.value)
  pdfSrc.value = ''
  bpStore.pdfSrc = ''
  bpStore.pdfFile = null
  bpStore.pdfPath = ''
  releaseObjectUrl(bpStore.excelSrc)
  bpStore.excelSrc = ''
  bpStore.excelFile = null
  bpStore.excelPath = ''
  bpStore.fieldNames = []
  bpStore.excelContent = []
  bpStore.iconList = []
  bpStore.templateType = 'pdf'
  bpStore.docxFile = null
  bpStore.docxPath = ''
  bpStore.docxStructure = []
  bpStore.loopBlocks = []
  nameParts.value = []
  customText.value = ''
  insertIndex.value = 0
  templateMtime.value = null
  excelMtime.value = null
  docxDiskBytes = null
  // 重置后视为一份全新的内容，下次保存创建新项目（不覆盖已有项目）
  bpStore.clearCurrentProject()
  // 材料被清空，保存按钮回到「暂无改动」状态
  savedProgressSignature.value = progressSignature()
}

/* ===== 重置 / 清空标注：先弹确认框，避免误触 ===== */
const confirmKind = ref<'reset' | 'clearIcons' | null>(null)

const confirmConfig = computed(() => {
  if (confirmKind.value === 'reset') {
    return {
      title: '确定重置当前内容？',
      message: '将清空模板、表格、材料、循环块与文件名规则，并解除与当前项目的关联。此操作不可撤销。',
      confirmText: '确定重置',
    }
  }
  if (confirmKind.value === 'clearIcons') {
    return {
      title: '确定清空全部标注？',
      message: `将移除当前 ${bpStore.iconList.length} 个标注，未保存的改动会丢失。此操作不可撤销。`,
      confirmText: '确定清空',
    }
  }
  return null
})

/** 重置：没有任何内容时不弹框，直接忽略 */
function requestReset() {
  const hasContent = hasAnyPath.value || bpStore.iconList.length > 0 || nameParts.value.length > 0
  if (!hasContent) {
    notifyProgress('当前没有可重置的内容')
    return
  }
  confirmKind.value = 'reset'
}

/** 清空标注：没有标注时不弹框 */
function requestClearIcons() {
  if (bpStore.iconList.length === 0) return
  confirmKind.value = 'clearIcons'
}

function onConfirmDialogToggle(value: boolean) {
  if (!value) confirmKind.value = null
}

function confirmAction() {
  const kind = confirmKind.value
  confirmKind.value = null
  if (kind === 'reset') handleReset()
  else if (kind === 'clearIcons') bpStore.iconList = []
}

/* ========= 工作进度：保存 / 恢复 ========= */
const saveDialog = ref(false)
const savingProgress = ref(false)
const saveTitle = ref('')
const historyDialog = ref(false)
const restoringRevisionKey = ref('')
const progressSnackbar = ref(false)
const progressMessage = ref('')

/**
 * 当前编辑内容的签名，用于判断「保存工作进度」是否有新改动。
 * 以材料（iconList）为核心，同时带上会写进快照的其它状态，
 * 避免只换了模板/表格或文件名规则时被误判为“没有改动”。
 */
function progressSignature(): string {
  return JSON.stringify({
    templateType: bpStore.templateType,
    templatePath: templatePath.value,
    excelPath: bpStore.excelPath,
    pdfScale: bpStore.pdfScale,
    iconList: bpStore.iconList,
    loopBlocks: bpStore.loopBlocks,
    nameParts: nameParts.value,
  })
}

/** 最近一次保存 / 恢复时的签名基线 */
const savedProgressSignature = ref(progressSignature())

/**
 * 是否可以保存：
 * - PDF：内容有变化（材料等）才能保存，没改动时按钮不可用；
 * - DOCX：正文改动只在保存时从编辑器取，无法在此判断，保持可用。
 */
const canSaveProgress = computed(() => {
  if (!hasTemplate.value) return false
  if (bpStore.templateType === 'docx') return true
  return progressSignature() !== savedProgressSignature.value
})

function notifyProgress(message: string) {
  progressMessage.value = message
  progressSnackbar.value = true
}

function goHistory() {
  progressSnackbar.value = false
  router.push('/history')
}

function defaultSaveTitle(): string {
  // 项目名称保持稳定，不再附带时间戳；每次保存的时间在项目历史里体现
  return templateFileName.value.replace(/\.[^.]+$/, '') || '未命名项目'
}

function openSaveDialog() {
  if (!hasTemplate.value) {
    notifyProgress('请先选择模板文件')
    return
  }
  if (!canSaveProgress.value) {
    notifyProgress('材料没有变化，无需保存')
    return
  }
  if (!bpStore.excelFile) {
    notifyProgress('请先选择 Excel 数据文件')
    return
  }
  // 已有项目时沿用它的名称，避免每次保存都被默认时间戳覆盖
  saveTitle.value = bpStore.currentProjectTitle || defaultSaveTitle()
  saveDialog.value = true
}

function openProjectHistory() {
  if (!bpStore.currentProjectId) {
    notifyProgress('当前内容还没有保存成项目')
    return
  }
  historyDialog.value = true
}

function openProjectHistoryFromSnackbar() {
  progressSnackbar.value = false
  openProjectHistory()
}

/** 深拷贝，避免把 Pinia 的响应式代理写进 JSON 快照 */
function clonePlain<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

/** 逐字节比较，用于判断编辑器内的 DOCX 是否已写回磁盘 */
function bytesEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false
  }
  return true
}

async function persistProgress(options: { exportAfter?: boolean } = {}) {
  const tplPath = templatePath.value
  if (!bpStore.dataPath) {
    notifyProgress('数据目录未就绪，无法保存')
    return
  }
  if (!tplPath || !bpStore.excelPath) {
    notifyProgress('请先选择模板与 Excel 数据')
    return
  }

  savingProgress.value = true
  try {
    // DOCX 模板的字段/图片是直接写进文档的，保存时把编辑器内容写回原文件，
    // 这样“路径即真相”才能成立；PDF 模板不被改写，无需回写。
    if (bpStore.templateType === 'docx') {
      const edited = await docxViewerRef.value?.getDocxArrayBuffer?.() ?? null
      if (edited) {
        const editedBytes = new Uint8Array(edited)
        const unchanged = docxDiskBytes !== null && bytesEqual(editedBytes, docxDiskBytes)
        if (!unchanged) {
          const ok = window.confirm(`将把编辑器中的最新内容写回模板原文件：\n${tplPath}\n\n原文件会被覆盖且不可撤销，是否继续？`)
          if (!ok) {
            saveDialog.value = false
            notifyProgress('已取消保存')
            return
          }
          try {
            await writeFile(tplPath, editedBytes)
            docxDiskBytes = editedBytes
            await refreshTemplateMtime()
          } catch (error) {
            console.error('回写 DOCX 模板失败:', error)
            notifyProgress(`模板回写失败（文件可能被占用或只读）：${(error as Error)?.message || '未知错误'}`)
            return
          }
        }
      }
    }

    const title = saveTitle.value.trim() || defaultSaveTitle()
    const projectId = bpStore.currentProjectId || undefined

    const snapshot = await saveWorkspace({
      dataPath: bpStore.dataPath,
      id: projectId,
      title,
      templateType: bpStore.templateType,
      templatePath: tplPath,
      excelPath: bpStore.excelPath,
      pdfScale: bpStore.pdfScale,
      iconList: clonePlain(bpStore.iconList),
      loopBlocks: clonePlain(bpStore.loopBlocks),
      docxStructure: clonePlain(bpStore.docxStructure),
      nameParts: clonePlain(nameParts.value),
    })

    // 记住项目 ID：后续保存继续写入同一个项目，旧版本进入项目历史
    bpStore.setCurrentProject(snapshot.id, title)
    // 记下当前材料状态，作为「保存工作进度」是否有新改动的基线
    savedProgressSignature.value = progressSignature()
    await refreshProjectRevisionCount()
    bpStore.bumpWorkspaces()
    saveDialog.value = false
    notifyProgress(projectId ? '已保存为该项目的新版本' : '项目已保存')

    if (options.exportAfter) {
      const exported = await exportWorkspaceJson(clonePlain(snapshot))
      if (exported) notifyProgress(`已导出到：${exported}`)
    }
  } catch (error) {
    console.error('保存工作进度失败:', error)
    notifyProgress(`保存失败：${(error as Error)?.message || '未知错误'}`)
  } finally {
    savingProgress.value = false
  }
}

/** 用历史记录快照重建现场：按路径重读模板/表格，再恢复字段、文件名规则、标注与循环块 */
async function applyWorkspace(snapshot: WorkspaceSnapshot) {
  if (!(await exists(snapshot.templatePath))) {
    notifyProgress('该记录的模板文件已被移动或删除，无法恢复')
    return
  }
  if (!(await exists(snapshot.excelPath))) {
    notifyProgress('该记录的表格文件已被移动或删除，无法恢复')
    return
  }

  // handleReset 会清空项目关联，先记下当前项目名称，供同项目内恢复旧版本时保留
  const previousProjectId = bpStore.currentProjectId
  const previousProjectTitle = bpStore.currentProjectTitle

  // 先清空当前会话，避免上一个模板的标注残留
  handleReset()

  bpStore.pdfScale = snapshot.pdfScale ?? 2

  await loadTemplateFromPath(snapshot.templatePath, { keepAnnotations: true })
  await loadExcelFromPath(snapshot.excelPath)

  // 标注与循环块不来自文件，直接取自快照
  bpStore.iconList = snapshot.iconList ?? []
  bpStore.loopBlocks = snapshot.loopBlocks ?? []
  nameParts.value = snapshot.nameParts ?? []
  insertIndex.value = nameParts.value.length

  // 继续编辑 / 再次保存都归入同一个项目；
  // 同一项目内恢复旧版本时保留项目当前名称，避免被历史版本的名称覆盖
  const keepTitle = previousProjectId === snapshot.id ? previousProjectTitle : ''
  bpStore.setCurrentProject(snapshot.id, keepTitle || snapshot.title || snapshot.id)
  await refreshProjectRevisionCount()

  // Excel 已按磁盘内容重解析：校验材料引用的字段是否仍然存在
  validateFieldReferences()

  // 刚恢复的版本即当前状态，保存按钮回到「暂无改动」，直到再次编辑
  savedProgressSignature.value = progressSignature()

  notifyProgress(`已恢复「${snapshot.title}」，可继续编辑`)
}

/** 从项目历史弹窗恢复指定版本：先确认，再重建现场 */
async function restoreRevision(snapshot: WorkspaceSnapshot) {
  const key = revisionKey(snapshot)
  if (restoringRevisionKey.value) return
  const ok = window.confirm(
    `将把项目恢复到 ${formatDateTime(snapshot.savedAt)} 的版本：\n${snapshot.title}\n\n当前未保存的改动会丢失（已保存的版本不受影响），是否继续？`,
  )
  if (!ok) return

  restoringRevisionKey.value = key
  try {
    await applyWorkspace(snapshot)
    historyDialog.value = false
  } finally {
    restoringRevisionKey.value = ''
  }
}

function formatDateTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

async function applyPendingRestore() {
  const snapshot = bpStore.consumeRestore()
  if (!snapshot) return
  await applyWorkspace(snapshot)
}

/* ========= DOCX 循环块（字段/图片拖放由 DocxViewer 直接写入文档，不再走 iconList） ========= */
function openLoopBlockDialog(payload: { anchorId: string; loopType: 'paragraph' | 'tableRow' }) {
  pendingAnchorId.value = payload.anchorId
  pendingLoopType.value = payload.loopType
  const existing = bpStore.loopBlocks.find(b => b.anchorId === payload.anchorId)
  if (existing) {
    currentLoopBlock.value = existing
    loopBlockForm.value = {
      loopVar: existing.loopVar,
      listVar: existing.listVar,
      dataRange: existing.dataRange,
      rangeColumn: existing.rangeColumn,
      conditions: JSON.parse(JSON.stringify(existing.conditions)),
      matchMode: existing.matchMode,
    }
  } else {
    currentLoopBlock.value = null
    loopBlockForm.value = {
      loopVar: 'item',
      listVar: '明细',
      dataRange: 'all',
      rangeColumn: undefined,
      conditions: [],
      matchMode: '所有',
    }
  }
  loopBlockDialog.value = true
}

function addLoopCondition() {
  loopBlockForm.value.conditions.push({
    id: Date.now(),
    field: null,
    op: '等于',
    value: '',
  })
}

function removeLoopCondition(idx: number) {
  loopBlockForm.value.conditions.splice(idx, 1)
}

function saveLoopBlock() {
  const anchorId = currentLoopBlock.value?.anchorId ?? pendingAnchorId.value
  const loopType = currentLoopBlock.value?.loopType ?? pendingLoopType.value
  if (!anchorId) return
  const block: LoopBlock = {
    id: currentLoopBlock.value?.id ?? Date.now(),
    anchorId,
    loopType,
    loopVar: loopBlockForm.value.loopVar || 'item',
    listVar: loopBlockForm.value.listVar || '明细',
    dataRange: loopBlockForm.value.dataRange,
    rangeColumn: loopBlockForm.value.rangeColumn,
    conditions: JSON.parse(JSON.stringify(loopBlockForm.value.conditions)),
    matchMode: loopBlockForm.value.matchMode,
  }
  const idx = bpStore.loopBlocks.findIndex(b => b.anchorId === anchorId)
  if (idx >= 0) {
    bpStore.loopBlocks[idx] = block
  } else {
    bpStore.loopBlocks.push(block)
  }
  loopBlockDialog.value = false
}

function deleteLoopBlock() {
  if (!currentLoopBlock.value) return
  const idx = bpStore.loopBlocks.findIndex(b => b.anchorId === currentLoopBlock.value!.anchorId)
  if (idx >= 0) {
    bpStore.loopBlocks.splice(idx, 1)
  }
  loopBlockDialog.value = false
}
</script>

<style scoped>
.batch-shell {
  max-width: 1600px;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.batch-grid {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.batch-col {
  display: flex;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  padding-bottom: 12px;
}

/* 小屏下列上下堆叠时，高度由内容决定，整列在 batch-grid 内部滚动 */
@media (max-width: 1279.98px) {
  .batch-grid {
    overflow-y: auto;
  }

  .batch-col {
    height: auto;
  }
}

/* ---- cards ---- */
.control-card,
.preview-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  width: 100%;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  padding: 16px 20px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.card-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: rgb(15, 23, 42);
  letter-spacing: -0.01em;
}

.preview-top {
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.clear-chip {
  cursor: pointer;
  font-weight: 500;
}

.confirm-title {
  font-size: 1rem !important;
  font-weight: 600;
}

.confirm-text {
  font-size: 0.84rem !important;
  color: rgb(71, 85, 105) !important;
  line-height: 1.6;
}

.preview-actions {
  flex-wrap: wrap;
}

.project-chip {
  cursor: pointer;
  max-width: 190px;
  font-weight: 500;
}

.project-chip-name {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-icon-btn {
  flex: none;
}

.save-progress-btn {
  text-transform: none;
  letter-spacing: normal;
  font-weight: 500;
}

.file-picked-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  padding-left: 2px;
  font-size: 0.72rem;
  color: rgb(71, 85, 105);
}

.pick-file-btn {
  justify-content: flex-start;
  text-transform: none;
  letter-spacing: normal;
  font-weight: 500;
  font-size: 0.78rem;
}

.file-meta-row {
  margin-top: 4px;
  padding-left: 2px;
  font-size: 0.68rem;
  color: rgb(148, 163, 184);
}

.invalid-field-list {
  margin: 8px 0 0 0;
  padding-left: 20px;
  font-size: 0.8rem;
  color: rgb(71, 85, 105);
}

.file-picked-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.save-summary {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.03);
  font-size: 0.78rem;
  color: rgb(71, 85, 105);
}

.save-summary-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.save-summary-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---- sections ---- */
.control-body {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto auto;
  gap: 0;
  min-height: 0;
  flex: 1;
  overflow: hidden;
  padding: 4px 20px 16px;
}

.section {
  padding: 12px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.03);
}

.section:last-of-type {
  border-bottom: none;
}

.section-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: rgb(100, 116, 139);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}

.field-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.material-nav {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 4px;
}

.material-nav-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 0;
  min-height: 34px;
  padding: 4px 5px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: color-mix(in srgb, var(--material-color) 8%, white);
  color: var(--material-color);
  cursor: pointer;
  font: inherit;
  font-size: 0.72rem;
  font-weight: 600;
  transition: background 0.15s, border-color 0.15s, transform 0.15s;
}

.material-nav-item:hover,
.material-nav-item.active {
  background: color-mix(in srgb, var(--material-color) 16%, white);
  border-color: color-mix(in srgb, var(--material-color) 30%, white);
  transform: translateY(-1px);
}

.material-nav-item--table { --material-color: #2563eb; }
.material-nav-item--signature { --material-color: #0f766e; }
.material-nav-item--seal { --material-color: #c2410c; }
.material-nav-item--icon { --material-color: #7c3aed; }
.material-nav-item--text { --material-color: #be185d; }

.material-nav-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.material-nav-item:focus-visible {
  outline: 2px solid rgba(79, 140, 255, 0.45);
  outline-offset: 1px;
}

.material-expand-host {
  flex: 1;
  min-height: 0;
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.material-stage-inner {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.material-fade-enter-active,
.material-fade-leave-active {
  transition: opacity 0.14s ease;
}

.material-fade-enter-from,
.material-fade-leave-to {
  opacity: 0;
}

.expand-empty-tip {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  color: rgb(148, 163, 184);
  text-align: center;
}

/* ---- field chips ---- */
.field-chip-list {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 6px;
  padding: 4px 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.field-chip {
  padding: 6px 12px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(79,140,255,0.08), rgba(108,92,231,0.05));
  border: 1px solid rgba(79,140,255,0.35);
  cursor: grab;
  transition: all 0.15s ease;
  user-select: none;
  font-size: 0.78rem;
  font-weight: 500;
  color: #2563eb;
}

.field-chip:hover {
  background: linear-gradient(135deg, rgba(79,140,255,0.15), rgba(108,92,231,0.1));
  border-color: rgba(79,140,255,0.55);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(79,140,255,0.15);
}

.field-chip:active {
  cursor: grabbing;
  transform: translateY(0);
}

/* ---- signature / seal thumbnails ---- */
.thumb-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  /* 容器定高且内容溢出时，auto 行轨道会坍缩到最小尺寸导致卡片重叠，
     强制按内容（卡片 aspect-ratio 推导高度）决定行高 */
  grid-auto-rows: max-content;
  align-content: start;
  gap: 6px;
  padding: 4px 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.thumb-card {
  aspect-ratio: 1;
  border-radius: 10px;
  background: #f1f5f9;
  border: 2px solid transparent;
  cursor: grab;
  overflow: hidden;
  transition: all 0.15s ease;
  opacity: 0.85;
}

.thumb-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 透明底的签字 / 印章用棋盘格衬底，便于确认背景是否已去除 */
.thumb-card--signature,
.thumb-card--seal {
  background-color: #fff;
  background-image:
    linear-gradient(45deg, #eef2f7 25%, transparent 25%, transparent 75%, #eef2f7 75%),
    linear-gradient(45deg, #eef2f7 25%, transparent 25%, transparent 75%, #eef2f7 75%);
  background-size: 12px 12px;
  background-position: 0 0, 6px 6px;
}

.thumb-card--signature img,
.thumb-card--seal img {
  object-fit: contain;
  padding: 4px;
}

.thumb-card:hover {
  opacity: 1;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.thumb-card--signature:hover {
  border-color: rgba(15,118,110,0.45);
}

.thumb-card--seal:hover {
  border-color: rgba(194,65,12,0.45);
}

.thumb-card:active {
  cursor: grabbing;
  transform: translateY(0);
}

/* ---- signature / seal add card ---- */
.thumb-add {
  cursor: pointer;
  opacity: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed rgba(100, 116, 139, 0.4);
  background: rgba(100, 116, 139, 0.06);
  color: rgba(100, 116, 139, 0.7);
  font: inherit;
}

.thumb-add:hover {
  border-style: solid;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.thumb-add:active {
  cursor: pointer;
  transform: translateY(0);
}

.thumb-add--signature {
  border-color: rgba(15, 118, 110, 0.45);
  background: rgba(15, 118, 110, 0.05);
  color: rgba(15, 118, 110, 0.8);
}

.thumb-add--seal {
  border-color: rgba(194, 65, 12, 0.45);
  background: rgba(194, 65, 12, 0.05);
  color: rgba(194, 65, 12, 0.8);
}

.hidden-file-input {
  display: none;
}

/* ---- icon mini grid ---- */
.icon-mini-grid {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 4px 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.icon-mini-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.icon-mini-label {
  font-size: 0.68rem;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.icon-mini-row {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
}

.icon-mini-cell {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  font-family: "Segoe UI Symbol", "Segoe UI Emoji", sans-serif;
  font-size: 16px;
  cursor: grab;
  background: #f8fafc;
  border: 1px solid transparent;
  transition: all 0.12s ease;
}

.icon-mini-cell:hover {
  background: linear-gradient(135deg, rgba(124,58,237,0.1), rgba(168,85,247,0.05));
  border-color: rgba(124,58,237,0.35);
  color: #7c3aed;
  transform: scale(1.1);
}

.icon-mini-cell:active {
  cursor: grabbing;
  transform: scale(1);
}

/* ---- text presets ---- */
.text-stage {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.text-preset-list {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 6px;
  padding: 4px 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.text-preset-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 5px 6px 5px 12px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(190,24,93,0.07), rgba(219,39,119,0.04));
  border: 1px solid rgba(190,24,93,0.35);
  cursor: grab;
  transition: all 0.15s ease;
  user-select: none;
}

.text-preset-chip:hover {
  background: linear-gradient(135deg, rgba(190,24,93,0.12), rgba(219,39,119,0.08));
  border-color: rgba(190,24,93,0.55);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(190,24,93,0.15);
}

.text-preset-chip:active {
  cursor: grabbing;
  transform: translateY(0);
}

.text-preset-label {
  font-size: 0.8rem;
  max-width: 180px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.text-preset-del {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: rgba(190,24,93,0.12);
  color: #be185d;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s;
}

.text-preset-del:hover {
  background: #be185d;
  color: #fff;
}

.text-preset-add {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border-radius: 16px;
  border: 1px dashed rgba(190,24,93,0.45);
  background: rgba(190,24,93,0.04);
  color: #be185d;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.text-preset-add:hover {
  background: rgba(190,24,93,0.1);
  border-style: solid;
  transform: translateY(-1px);
}

/* ---- text preset dialog ---- */
.text-dialog-header {
  display: flex;
  align-items: center;
  padding-bottom: 0;
}

.text-dialog-title {
  font-size: 1.05rem;
  font-weight: 700;
}

.text-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 8px !important;
}

.text-dialog-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.text-dialog-row > .v-icon {
  flex-shrink: 0;
}

.text-dialog-select {
  flex: 1;
  min-width: 0;
}

.text-dialog-select :deep(.v-field) {
  border-radius: 8px !important;
  box-shadow: none !important;
}

.text-weight-toggle {
  border-radius: 8px;
  overflow: hidden;
}

.text-weight-toggle :deep(.v-btn) {
  min-width: 48px !important;
  padding: 0 12px !important;
  height: 28px !important;
  font-size: 12px !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
}

.text-size-field {
  width: 88px;
  flex-shrink: 0;
}

.text-size-field :deep(.v-field) {
  border-radius: 8px !important;
  box-shadow: none !important;
}

.text-dialog-slider {
  flex: 1;
  min-width: 0;
}

.text-color-swatch {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  border: 1.5px solid rgba(0,0,0,0.15);
  flex-shrink: 0;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.text-color-swatch:hover {
  transform: scale(1.1);
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.text-color-hex {
  font-size: 12px;
  font-weight: 500;
  color: #475569;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.text-preview-box {
  padding: 14px 12px;
  border-radius: 12px;
  background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%);
  border: 1px solid rgba(190,24,93,0.12);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 64px;
  gap: 6px;
}

.text-preview-label {
  font-size: 10px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.text-preview-value {
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.text-dialog-actions {
  padding: 8px 16px 16px;
}

/* ---- filename ---- */
.filename-section {
  overflow-y: auto;
  max-height: 220px;
  overscroll-behavior: contain;
}

.name-input {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  min-height: 46px;
  padding: 8px 10px;
  border: 1px solid rgba(0, 0, 0, 0.16);
  border-radius: 8px;
  transition: border-color 0.15s;
  cursor: text;
}

.name-input:hover {
  border-color: rgba(0, 0, 0, 0.4);
}

.name-input:focus {
  outline: none;
  border-color: rgb(var(--v-theme-primary));
}

.insert-gap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 9px;
  height: 26px;
  cursor: text;
  flex: 0 0 auto;
}

.insert-gap::after {
  content: '';
  width: 2px;
  height: 18px;
  border-radius: 1px;
  background: transparent;
  transition: background 0.1s;
}

.insert-gap:hover::after {
  background: rgba(0, 0, 0, 0.2);
}

.insert-gap--active::after {
  background: rgb(var(--v-theme-primary));
  animation: caret-blink 1s step-end infinite;
}

@keyframes caret-blink {
  50% {
    opacity: 0;
  }
}

.name-placeholder {
  font-size: 0.78rem;
  color: rgb(148, 163, 184);
  cursor: text;
}

.name-add-btn {
  margin-left: auto;
}

.custom-text-input {
  min-width: 130px;
}

.name-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 6px 10px;
  background: rgb(248, 250, 252);
  border: 1px dashed rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  min-width: 0;
}

.preview-label {
  flex: 0 0 auto;
  font-size: 0.68rem;
  font-weight: 600;
  color: rgb(148, 163, 184);
  letter-spacing: 0.04em;
}

.name-preview .path-mono {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---- buttons ---- */
.generate-btn {
  margin-top: 12px;
  border-radius: 12px !important;
}

.generate-progress {
  margin-top: 10px;
}

.generate-progress-text {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
  font-variant-numeric: tabular-nums;
}

/* ---- preview ---- */
.preview-surface {
  /* 把预览区限制成可收缩的 flex 子项，确保内部滚动不会推动外层布局 */
  flex: 1 1 0;
  height: 0; /* 关键：与父容器的 flex 布局配合，约束高度 */
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin: 0 12px 12px;
  border-radius: 12px;
  overflow: hidden;
  background: rgb(248, 249, 250);
  border: 1px solid rgba(0, 0, 0, 0.04);
  box-sizing: border-box;
}

.preview-scroll {
  /* 占满父高度并由自身滚动 */
  flex: 1 1 0;
  height: 100%;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
}

.path-mono {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  word-break: break-all;
}

/* ---- 右键删除菜单 ---- */
.img-ctx-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1999;
}

.img-ctx-menu {
  position: fixed;
  z-index: 2000;
  min-width: 140px;
  padding: 4px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  animation: img-ctx-fade 0.1s ease;
}

@keyframes img-ctx-fade {
  from {
    opacity: 0;
    transform: scale(0.96);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.img-ctx-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #ef4444;
  font: inherit;
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s;
}

.img-ctx-item:hover {
  background: rgba(239, 68, 68, 0.08);
}
</style>
