<script setup>
import { mapStores } from "pinia"

import { HandThumbUpIcon, HandThumbDownIcon } from "@heroicons/vue/24/outline"
import { useAppStateStore } from "../stores/settings_store"

const appState = useAppStateStore()
</script>

<script>
export default {
  props: ["classifiers", "last_used_classifier_id"],
  emits: ["addToClassifier"],
  data() {
    return {
      selected_classifier_id: null,
      selected_classifier_class: "_default",
    }
  },
  watch: {
    selected_classifier_id() {
      this.selected_classifier_class =
        this.classifiers[
          this.classifiers.findIndex((e) => e.id == this.selected_classifier_id)
        ].actual_classes[0]
    },
  },
  computed: {},
  mounted() {
    if (this.last_used_classifier_id === null) {
      this.selected_classifier_id = this.classifiers.length ? this.classifiers[0].id : null
    } else {
      this.selected_classifier_id = this.last_used_classifier_id
    }
  },
  methods: {},
}
</script>

<template>
  <div class="flex flex-row">
    <select
      v-model="selected_classifier_id"
      class="mr-3 h-8 w-32 rounded-md border-transparent py-0 pl-2 pr-8 text-sm text-gray-500 ring-1 ring-gray-300 focus:border-blue-500 focus:ring-blue-500">
      <option v-for="classifier in classifiers" :value="classifier.id">
        {{ classifier.name }}
      </option>
    </select>
    <select
      v-if="selected_classifier_id !== null"
      v-model="selected_classifier_class"
      class="mr-3 h-8 w-32 rounded-md border-transparent py-0 pl-2 pr-8 text-sm text-gray-500 ring-1 ring-gray-300 focus:border-blue-500 focus:ring-blue-500">
      <option
        v-for="class_name in classifiers[
          classifiers.findIndex((e) => e.id == selected_classifier_id)
        ].actual_classes"
        :value="class_name">
        {{ class_name == "_default" ? "Items" : class_name }}
      </option>
    </select>
    <button
      @click="
        $emit('addToClassifier', selected_classifier_id, selected_classifier_class, true)
      "
      class="mr-3 w-10 rounded-md px-3 text-green-600/50 ring-1 ring-gray-300 hover:bg-green-100">
      <HandThumbUpIcon></HandThumbUpIcon>
    </button>
    <button
      @click="
        $emit('addToClassifier', selected_classifier_id, selected_classifier_class, false)
      "
      class="w-10 rounded-md px-3 text-red-600/50 ring-1 ring-gray-300 hover:bg-red-100">
      <HandThumbDownIcon></HandThumbDownIcon>
    </button>
  </div>
</template>

<style scoped></style>
