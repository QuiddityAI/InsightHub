<script setup>
import httpClient from "../../api/httpClient"

import {
  ChevronLeftIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline"

import ClassifierExampleList from "./ClassifierExampleList.vue"
import { FieldType } from "../../utils/utils"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
const appState = useAppStateStore()
</script>

<script>
export default {
  props: ["classifier_id", "class_name"],
  emits: ["close"],
  data() {
    return {
      selected_tab: "positives",
      classifier: useAppStateStore().classifiers.find((classifier) => classifier.id === this.classifier_id),
      positive_examples: [],
      negative_examples: [],
      target_vector_field: null,
      last_retraining: null,
      embedding_space_id: null,
      is_retraining: false,
      retraining_progress: 0.0,
      show_retrain_success_label: false,
    }
  },
  watch: {
    selected_tab() {
      if (this.selected_tab === "negatives") {
        this.load_examples(/* is_positive */ false)
      }
    },
  },
  computed: {
    ...mapStores(useAppStateStore),
    last_retraining_human_readable() {
      return new Date(this.last_retraining * 1000).toLocaleString()
    },
  },
  mounted() {
    this.target_vector_field = this.appStateStore.available_vector_fields.find((ds_and_field) => ds_and_field[1] === this.appStateStore.settings.vectorize.map_vector_field)
    if (!this.target_vector_field) {
      this.target_vector_field = this.appStateStore.available_vector_fields[0]
    }
    this.load_examples(/* is_positive */ true)
    this.get_training_status()
    this.get_retraining_status()
  },
  methods: {
    load_examples(is_positive) {
      const that = this
      const body = {
        classifier_id: this.classifier.id,
        class_name: this.class_name,
        type: FieldType.IDENTIFIER,
        is_positive: is_positive,
      }
      httpClient.post("/org/data_map/get_classifier_examples", body).then(function (response) {
        if (is_positive) {
          that.positive_examples = response.data
        } else {
          that.negative_examples = response.data
        }
      })
    },
    delete_classifier_class() {
      if (!confirm("Are you sure you want to delete this class and the list of examples?")) {
        return
      }
      const that = this
      const body = {
        classifier_id: this.classifier_id,
        class_name: this.class_name,
      }
      httpClient
        .post("/org/data_map/delete_classifier_class", body)
        .then(function (response) {
          const index = that.classifier.actual_classes.findIndex((classifier_class) => classifier_class.name === that.class_name)
          that.classifier.actual_classes.splice(index, 1)
          if (that.classifier.actual_classes.length === 0) {
            that.classifier.actual_classes.push({
              name: "_default",
              positive_count: 0,
              negative_count: 0,
            })
          }
        })
      this.$emit("close")
    },
    get_training_status() {
      const that = this
      const body = {
        class_name: this.class_name,
        target_vector_ds_and_field: this.target_vector_field,
      }
      httpClient.post(`/data_backend/classifier/${this.classifier_id}/training_status`, body)
      .then(function (response) {
        const status = response.data
        that.embedding_space_id = status.embedding_space_id
        that.last_retraining = status.time_updated
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    retrain() {
      const that = this
      if (this.is_retraining) {
        return
      }
      this.is_retraining = true
      this.retraining_progress = 0.0
      const body = {
        class_name: this.class_name,
        deep_train: false,
        target_vector_ds_and_field: this.target_vector_field,
      }
      httpClient.post(`/data_backend/classifier/${this.classifier_id}/retrain`, body)
      .then(function (response) {
        that.get_retraining_status()
      })
      .catch(function (error) {
        that.is_retraining = false
        that.retraining_progress = 0.0
        console.error(error)
      })
    },
    get_retraining_status() {
      const that = this
      httpClient.get(`/data_backend/classifier/${this.classifier_id}/retraining_status`)
      .then(function (response) {
        const status = response.data
        if (!status) {
          that.is_retraining = false
          that.retraining_progress = 0.0
        } else if (status.status === "done") {
          that.is_retraining = false
          that.retraining_progress = 0.0
          that.last_retraining = Math.floor(Date.now() / 1000)
          that.show_retrain_success_label = true
          setTimeout(() => {
            that.show_retrain_success_label = false
          }, 2000)
        } else if (status.status === "error") {
          that.is_retraining = false
          that.retraining_progress = 0.0
        } else {
          that.retraining_progress = status.progress
          setTimeout(that.get_retraining_status, 300)
        }
      })
      .catch(function (error) {
        that.is_retraining = false
        that.retraining_progress = 0.0
        console.error(error)
      })
    }
  },
}
</script>

<template>
  <div>
    <div class="mb-3 ml-1 mt-3 flex flex-row gap-3">
      <button
        @click="$emit('close')"
        class="h-6 w-6 rounded text-gray-400 hover:bg-gray-100">
        <ChevronLeftIcon></ChevronLeftIcon>
      </button>
      <span class="font-bold text-gray-600">{{ classifier.name }}:</span>
      <span class="text-medium text-gray-500">
        {{ class_name === '_default' ? 'Items' : class_name }} </span>

      <div class="flex-1"></div>

      <div class="w-40 h-6">
        <select
          v-model="target_vector_field"
          class="w-full py-0 rounded border-transparent text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
          <option v-for="item in appState.available_vector_fields" :value="item" selected>
            {{ appState.datasets[item[0]]?.name }}: {{ item[1] }}
          </option>
        </select>
      </div>

      <button
        class="relative h-6 items-center justify-center rounded-md text-gray-400 bg-gray-100"
        @click="retrain"
        :disabled="is_retraining"
        :title="`Last retraining: ${last_retraining_human_readable}, embedding space ${embedding_space_id}`">
        <div class="absolute h-full bg-blue-500/20 rounded-md" :style="{ width: `${retraining_progress * 100}%` }"></div>
        <span class="mx-2 hover:text-blue-500">{{ is_retraining ? "Retraining..." : (show_retrain_success_label ? "Retrained ✓": "Retrain") }}</span>
      </button>

      <button
        @click="delete_classifier_class"
        class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </button>
    </div>

    <div
      class="flex flex-row items-center justify-between text-center font-bold text-gray-400">
      <button
        v-for="item in [['positives', '+'], ['negatives', '-'], ['learn', 'Learn'], ['recommend', 'Recom.']]"
        class="flex-1"
        :class="{'text-blue-500': selected_tab === item[0]}"
        @click="selected_tab = item[0]">
        {{ item[1] }}
      </button>
    </div>
    <hr />

    <ClassifierExampleList
      v-if="selected_tab === 'positives'"
      :is_positive="true"
      :classifier_id="classifier_id"
      :class_name="class_name">
    </ClassifierExampleList>

    <ClassifierExampleList
      v-if="selected_tab === 'negatives'"
      :is_positive="false"
      :classifier_id="classifier_id"
      :class_name="class_name">
    </ClassifierExampleList>

    <div v-if="selected_tab === 'learn'">Learn</div>

    <div v-if="selected_tab === 'recommend'">Rec</div>

  </div>
</template>
