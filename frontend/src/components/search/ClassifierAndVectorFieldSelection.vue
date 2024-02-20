<script setup>
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
const appState = useAppStateStore()
</script>

<script>
export default {
  props: ['modelValue'],  // needed to make this component v-model-able
  emits: ['update:modelValue'],
  data() {
    return {
      selected_classifier_id: null,
      selected_classifier_class: "_default",
      target_ds_and_vector_field: [null, null],
    }
  },
  watch: {
    selected_classifier_id() {
      this.update_modelValue()
      if (this.selected_classifier_id === null) {
        this.selected_classifier_class = "_default"
        return
      }
      this.selected_classifier_class =
      this.appStateStore.classifiers[
          this.appStateStore.classifiers.findIndex((e) => e.id == this.selected_classifier_id)
        ].actual_classes[0].name
    },
    selected_classifier_class() {
      this.update_modelValue()
    },
    target_ds_and_vector_field() {
      this.update_modelValue()
    },
  },
  methods: {
    update_modelValue() {
      this.$emit('update:modelValue', {
        classifier_id: this.selected_classifier_id,
        class_name: this.selected_classifier_class,
        target_dataset_id: this.target_ds_and_vector_field[0],
        target_vector_field: this.target_ds_and_vector_field[1],
      })
    }
  },
  mounted() {
    if (this.appStateStore.last_used_classifier_id === null) {
      this.selected_classifier_id = this.appStateStore.classifiers.length ? this.appStateStore.classifiers[0].id : null
    } else {
      this.selected_classifier_id = this.appStateStore.last_used_classifier_id
    }
    this.target_ds_and_vector_field = this.appStateStore.available_vector_fields.find((ds_and_field) => ds_and_field[1] === this.appStateStore.settings.vectorize.map_vector_field)
    if (!this.target_ds_and_vector_field) {
      this.target_ds_and_vector_field = this.appStateStore.available_vector_fields[0]
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
  }
}
</script>

<template>
  <div class="flex flex-row">
    <div class="w-32 h-6">
      <select
        v-model="selected_classifier_id"
        class="w-full rounded-md border-transparent py-0 pl-2 pr-8 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
        <option v-for="classifier in appState.classifiers" :value="classifier.id">
          {{ classifier.name }}
        </option>
      </select>
    </div>
    <div class="w-24 h-6">
      <select
        v-if="selected_classifier_id !== null"
        v-model="selected_classifier_class"
        class="w-full rounded-md border-transparent py-0 pl-2 pr-8 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
        <option
          v-for="class_details in appState.classifiers[
            appState.classifiers.findIndex((e) => e.id == selected_classifier_id)
          ].actual_classes"
          :value="class_details.name">
          {{ class_details.name == "_default" ? "Items" : class_details.name }}
        </option>
      </select>
    </div>
    <div class="flex-1 h-6">
      <select
        v-model="target_ds_and_vector_field"
        class="w-full py-0 rounded border-transparent text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
        <option v-for="item in appState.available_vector_fields" :value="item" selected>
          {{ appState.datasets[item[0]]?.name }}: {{ item[1] }}
        </option>
      </select>
    </div>
  </div>
</template>
